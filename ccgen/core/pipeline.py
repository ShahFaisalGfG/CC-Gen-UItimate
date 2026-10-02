# pipeline.py - orchestrates audio extraction, transcription, translation, and subtitle output

import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from ccgen.config.defaults import (
    ComputeDefaults,
    ModelDefaults,
    OutputDefaults,
    TranscriptionDefaults,
    TranslationDefaults,
    TransliterationDefaults,
)
from ccgen.core import AnySegment, Segment, TranslatedSegment, TransliteratedSegment
from ccgen.core.audio import cleanup_temp, extract_audio
from ccgen.core.cues import CueBuilder, CueLayout, finalize_timing, join_unit_text, sentence_units, spread_translation
from ccgen.core.subtitle import (
    SubtitleSource,
    derive_output_path,
    write_ass,
    write_lrc,
    write_sbv,
    write_srt,
    write_vtt,
)
from ccgen.core.subtitle_parser import is_subtitle, parse_subtitle
from ccgen.engines.captions import create_engine as create_caption_engine
from ccgen.engines.captions.base import CaptionEngine
from ccgen.engines.translation import create_engine as create_translation_engine
from ccgen.engines.translation.base import TranslationEngine
from ccgen.engines.transliteration import create_engine as create_transliteration_engine
from ccgen.engines.transliteration.base import TransliterationEngine
from ccgen.utils.callbacks import JobCancelled, emit_progress, emit_segment, emit_status
from ccgen.utils.download_progress import cancellable

_log = logging.getLogger(__name__)

CANCELLED_MESSAGE = "Cancelled by user."

StatusCb = Optional[Callable[[str], None]]
ProgressCb = Optional[Callable[[int, int], None]]
SegmentCb = Optional[Callable[[AnySegment], None]]


@dataclass
class PipelineConfig:
    """All parameters needed to drive a single pipeline run."""

    input_path: str
    output_dir: Optional[str] = None
    model_name: str = ModelDefaults.DEFAULT_MODEL
    device: str = ComputeDefaults.DEFAULT_DEVICE
    compute_type: str = ComputeDefaults.DEFAULT_COMPUTE_TYPE
    language: Optional[str] = None
    translate: bool = False
    source_lang: str = TranslationDefaults.DEFAULT_SOURCE_LANG
    target_lang: str = TranslationDefaults.DEFAULT_TARGET_LANG
    emit_srt: bool = OutputDefaults.FORMAT_SRT
    emit_vtt: bool = OutputDefaults.FORMAT_VTT
    emit_lrc: bool = OutputDefaults.FORMAT_LRC
    emit_ass: bool = OutputDefaults.FORMAT_ASS
    emit_sbv: bool = OutputDefaults.FORMAT_SBV
    max_line_length: int = OutputDefaults.MAX_LINE_LENGTH
    max_lines: int = OutputDefaults.MAX_LINES
    beam_size: int = TranscriptionDefaults.BEAM_SIZE
    vad_filter: bool = TranscriptionDefaults.VAD_FILTER
    transliterate: bool = False
    translit_source: str = TransliterationDefaults.DEFAULT_SOURCE
    translit_target: str = TransliterationDefaults.DEFAULT_TARGET
    translit_input: str = TransliterationDefaults.INPUT_SOURCE
    translit_engine: str = TransliterationDefaults.DEFAULT_ENGINE


@dataclass
class PipelineResult:
    """Outcome of a completed pipeline run.

    `segments` holds the subtitle cues that were written (already split to the line limits),
    not the raw transcription segments.
    """

    success: bool
    input_path: str
    segments: list[Segment] = field(default_factory=list)
    translated_segments: list[TranslatedSegment] = field(default_factory=list)
    transliterated_segments: list[TransliteratedSegment] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    detected_language: str = ""
    error: str = ""
    cancelled: bool = False


class Pipeline:
    """Runs the full subtitle generation flow for a single media file."""

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self._cancel_event = threading.Event()
        self._layout = CueLayout(max_line_length=config.max_line_length, max_lines=config.max_lines)
        self._subtitle_input = is_subtitle(config.input_path)
        self._transcriber: Optional[CaptionEngine] = (
            None if self._subtitle_input
            else create_caption_engine(
                model_name=config.model_name,
                device=config.device,
                compute_type=config.compute_type,
            )
        )
        self._translator: Optional[TranslationEngine] = (
            create_translation_engine(source_lang=config.source_lang, target_lang=config.target_lang)
            if config.translate
            else None
        )
        self._transliterator: Optional[TransliterationEngine] = (
            create_transliteration_engine(
                config.translit_engine,
                source_scheme=config.translit_source,
                target_scheme=config.translit_target,
            )
            if config.transliterate
            else None
        )

    def cancel(self) -> None:
        """Ask a running prepare()/run() to stop at the next segment or download chunk."""
        self._cancel_event.set()

    @property
    def cancelled(self) -> bool:
        """True once cancel() has been called."""
        return self._cancel_event.is_set()

    def prepare(
        self,
        progress_cb: StatusCb = None,
        progress_num_cb: ProgressCb = None,
    ) -> None:
        """Load all models, downloading on first use. Call once before run().

        Skips Whisper loading when the input is a subtitle file. The translator model is
        pre-loaded only when the source language is explicit (not 'auto'). Raises RuntimeError
        on model load failure so the caller can surface it early, and JobCancelled when the job
        is cancelled mid-download.
        """
        with cancellable(self._cancel_event.is_set):
            if self._transcriber is not None:
                self._transcriber.load(progress_cb, progress_num_cb)
            can_preload = (
                self._translator is not None
                and self._config.source_lang != "auto"
                and self._config.source_lang != self._config.target_lang
            )
            if can_preload:
                self._translator.ensure_model(progress_cb, progress_num_cb)  # type: ignore[union-attr]

    def run(
        self,
        progress_cb: StatusCb = None,
        segment_cb: SegmentCb = None,
        progress_num_cb: ProgressCb = None,
    ) -> PipelineResult:
        """Execute the full pipeline. Never raises; returns PipelineResult on success, failure, or cancel."""
        _log.info("Pipeline starting: %s", os.path.basename(self._config.input_path))
        status, segments_out, progress = self._guarded(progress_cb), self._guarded(segment_cb), self._guarded(progress_num_cb)
        audio_path: Optional[str] = None
        try:
            if not self._enabled_formats():
                raise ValueError("No output format selected. Enable at least one subtitle format.")
            with cancellable(self._cancel_event.is_set):
                if self._subtitle_input:
                    cues, detected_lang = self._load_subtitle(status, segments_out)
                else:
                    emit_status(status, "Extracting audio...")
                    audio_path = extract_audio(self._config.input_path)
                    self._check_cancelled()
                    cues, detected_lang = self._transcribe(audio_path, status, segments_out, progress)

                translated = self._translate(cues, detected_lang, status, progress, segments_out)
                transliterated = self._transliterate(cues, translated, status, progress, segments_out)
            self._check_cancelled()
            output_files = self._write_outputs(cues, translated, transliterated, detected_lang, status)

            emit_status(status, "Done.")
            return PipelineResult(
                success=True,
                input_path=self._config.input_path,
                segments=cues,
                translated_segments=translated,
                transliterated_segments=transliterated,
                output_files=output_files,
                detected_language=detected_lang,
            )
        except JobCancelled:
            _log.info("Pipeline cancelled: %s", self._config.input_path)
            return PipelineResult(
                success=False, input_path=self._config.input_path, error=CANCELLED_MESSAGE, cancelled=True,
            )
        except Exception as e:
            if self.cancelled:
                return PipelineResult(
                    success=False, input_path=self._config.input_path, error=CANCELLED_MESSAGE, cancelled=True,
                )
            msg = str(e) or repr(e)
            _log.error("Pipeline failed for %s: %r", self._config.input_path, e, exc_info=True)
            return PipelineResult(success=False, input_path=self._config.input_path, error=msg)
        finally:
            if audio_path:
                cleanup_temp(audio_path)

    def _guarded(self, fn: Optional[Callable]) -> Callable:
        """Wrap a callback so every call first checks for cancellation.

        Engines call their callbacks once per segment, which makes them the natural points
        to stop a long transcription; the wrapper exists even when the caller passed None.
        """

        def wrapper(*args) -> None:
            self._check_cancelled()
            if fn is not None:
                fn(*args)

        return wrapper

    def _check_cancelled(self) -> None:
        """Raise JobCancelled once cancel() has been requested."""
        if self._cancel_event.is_set():
            raise JobCancelled()

    def _transcribe(
        self,
        audio_path: str,
        status: Callable[[str], None],
        segment_cb: Callable[[AnySegment], None],
        progress: Callable[[int, int], None],
    ) -> tuple[list[Segment], str]:
        """Transcribe audio and split the result into subtitle cues, streaming cues as they form."""
        emit_status(status, "Transcribing...")
        builder = CueBuilder(self._layout)

        def on_segment(segment: Segment) -> None:
            for cue in builder.add(segment):
                emit_segment(segment_cb, cue)

        raw = self._transcriber.transcribe(  # type: ignore[union-attr]
            audio_path,
            language=self._config.language,
            beam_size=self._config.beam_size,
            vad_filter=self._config.vad_filter,
            progress_cb=status,
            segment_cb=on_segment,
            progress_num_cb=progress,
        )
        # Engines are expected to stream every segment, but anything they returned without
        # streaming still has to become cues.
        for segment in raw[builder.source_count:]:
            builder.add(segment)
        for cue in builder.flush():
            emit_segment(segment_cb, cue)
        detected_lang = raw[0]["language"] if raw else (self._config.language or "")
        return finalize_timing(builder.cues, self._layout), detected_lang

    def _load_subtitle(
        self,
        status: Callable[[str], None],
        segment_cb: Callable[[AnySegment], None],
    ) -> tuple[list[Segment], str]:
        """Parse the subtitle input file and stream each segment to the UI, keeping its timing."""
        emit_status(status, "Reading subtitle file...")
        segments = parse_subtitle(self._config.input_path)
        detected_lang = self._config.language or ""
        for seg in segments:
            seg["language"] = detected_lang
            emit_segment(segment_cb, seg)
        return segments, detected_lang

    def _translate(
        self,
        cues: list[Segment],
        detected_lang: str,
        status: Callable[[str], None],
        progress: Callable[[int, int], None],
        segment_cb: Callable[[AnySegment], None],
    ) -> list[TranslatedSegment]:
        """Translate whole sentences, then spread each translation back over its cues.

        Cues are often half-sentence fragments; translating them one by one loses the
        context a sentence-level model needs, especially between languages with different
        word order (e.g. English to Urdu).
        """
        if self._translator is None or not cues:
            return []
        target = self._config.target_lang
        src = detected_lang if self._config.source_lang == "auto" else self._config.source_lang
        if not src:
            raise RuntimeError(
                "Source language is required for translation. "
                "Set a specific language (not Auto-detect) when translating subtitle files."
            )
        if src == target:
            emit_status(status, f"Translation skipped: the source is already in '{target}'.")
            return []
        try:
            emit_status(status, "Translating...")
            units = sentence_units(cues)
            unit_segments = [
                Segment(
                    id=idx,
                    start=cues[members[0]]["start"],
                    end=cues[members[-1]]["end"],
                    text=join_unit_text([cues[i] for i in members], src),
                    words=[],
                    language=src,
                )
                for idx, members in enumerate(units)
            ]

            def spread(unit: TranslatedSegment) -> list[TranslatedSegment]:
                return spread_translation([cues[i] for i in units[unit["id"]]], unit["translated"], target)

            def on_unit(unit: TranslatedSegment) -> None:
                for part in spread(unit):
                    emit_segment(segment_cb, part)

            _log.debug("Translating %d sentences (%d cues): %s → %s", len(units), len(cues), src, target)
            self._translator.set_pair(src, target)
            self._translator.ensure_model(status, progress)
            translated_units = self._translator.translate_segments(unit_segments, status, progress, on_unit)
            return [part for unit in translated_units for part in spread(unit)]
        except JobCancelled:
            raise
        except Exception as e:
            _log.error("Translation step failed: %r", e, exc_info=True)
            raise RuntimeError(f"Translation step failed: {e}") from e

    def _transliterate(
        self,
        cues: list[Segment],
        translated: list[TranslatedSegment],
        status: Callable[[str], None],
        progress: Callable[[int, int], None],
        segment_cb: Callable[[AnySegment], None],
    ) -> list[TransliteratedSegment]:
        """Run transliteration when enabled; picks input from transcription or translation."""
        if self._transliterator is None or not cues:
            return []
        try:
            emit_status(status, "Transliterating...")
            source_segs: list[Segment] | list[TranslatedSegment] = (
                translated if self._config.translit_input == "translation" and translated
                else cues
            )
            return self._transliterator.transliterate_segments(source_segs, status, progress, segment_cb)
        except JobCancelled:
            raise
        except Exception as e:
            _log.error("Transliteration step failed: %r", e, exc_info=True)
            raise RuntimeError(f"Transliteration step failed: {e}") from e

    def _write_outputs(
        self,
        cues: list[Segment],
        translated: list[TranslatedSegment],
        transliterated: list[TransliteratedSegment],
        detected_lang: str,
        status: Callable[[str], None],
    ) -> list[str]:
        """Write all requested subtitle files and return their paths."""
        emit_status(status, "Writing subtitle files...")
        if self._config.output_dir:
            os.makedirs(self._config.output_dir, exist_ok=True)
        out: list[str] = []
        cfg = self._config
        if not self._subtitle_input:
            out += self._write_flavor(cues, False, "", detected_lang)
        if translated:
            out += self._write_flavor(translated, True, f"_{cfg.target_lang}", cfg.target_lang)
        if transliterated:
            suffix = f"_tr_{cfg.translit_source}_{cfg.translit_target}"
            out += self._write_flavor(transliterated, True, suffix, cfg.translit_target)
        return out

    def _enabled_formats(self) -> list[tuple[str, Callable[..., str]]]:
        """Return (extension, writer) pairs for every subtitle format enabled in this config."""
        candidates = [
            (".srt", self._config.emit_srt, write_srt),
            (".vtt", self._config.emit_vtt, write_vtt),
            (".lrc", self._config.emit_lrc, write_lrc),
            (".ass", self._config.emit_ass, write_ass),
            (".sbv", self._config.emit_sbv, write_sbv),
        ]
        return [(ext, writer) for ext, enabled, writer in candidates if enabled]

    def _write_flavor(
        self,
        segments: SubtitleSource,
        translated_flag: bool,
        suffix: str,
        language: str,
    ) -> list[str]:
        """Write every enabled format for one segment flavor (original/translated/transliterated)."""
        layout = self._layout.for_language(language)
        written: list[str] = []
        for ext, writer in self._enabled_formats():
            path = self._out_path(self._config.input_path, suffix, ext)
            writer(
                segments, path, translated=translated_flag,
                max_line_length=layout.max_line_length, max_lines=layout.max_lines,
            )
            written.append(path)
        return written

    def _out_path(self, input_path: str, suffix: str, ext: str) -> str:
        """Build an output file path, relocating to output_dir when set."""
        candidate = derive_output_path(input_path, suffix, ext)
        if self._config.output_dir:
            return os.path.join(self._config.output_dir, os.path.basename(candidate))
        return candidate
