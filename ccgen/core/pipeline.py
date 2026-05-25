# pipeline.py — orchestrates audio extraction, transcription, translation, and subtitle output

import os
from dataclasses import dataclass, field
from typing import Callable, Optional

from ccgen.config.defaults import OutputDefaults, TranslationDefaults
from ccgen.core import Segment, TranslatedSegment
from ccgen.core.audio import cleanup_temp, extract_audio
from ccgen.core.subtitle import derive_output_path, write_srt, write_vtt
from ccgen.core.transcriber import Transcriber
from ccgen.core.translator import Translator


@dataclass
class PipelineConfig:
    """All parameters needed to drive a single pipeline run."""

    input_path: str
    output_dir: Optional[str] = None
    model_name: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    language: Optional[str] = None
    translate: bool = False
    source_lang: str = TranslationDefaults.DEFAULT_SOURCE_LANG
    target_lang: str = TranslationDefaults.DEFAULT_TARGET_LANG
    emit_srt: bool = OutputDefaults.FORMAT_SRT
    emit_vtt: bool = OutputDefaults.FORMAT_VTT
    beam_size: int = 5
    vad_filter: bool = True


@dataclass
class PipelineResult:
    """Outcome of a completed pipeline run."""

    success: bool
    input_path: str
    segments: list[Segment] = field(default_factory=list)
    translated_segments: list[TranslatedSegment] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    detected_language: str = ""
    error: str = ""


class Pipeline:
    """Runs the full subtitle generation flow for a single media file."""

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self._transcriber = Transcriber(
            model_name=config.model_name,
            device=config.device,
            compute_type=config.compute_type,
        )
        self._translator: Optional[Translator] = (
            Translator(source_lang=config.source_lang, target_lang=config.target_lang)
            if config.translate
            else None
        )

    def prepare(self, progress_cb: Optional[Callable[[str], None]] = None) -> None:
        """Load all models, downloading on first use. Call once before run().

        Translator model is pre-loaded only when source language is explicit (not 'auto'),
        because auto-detection requires transcription to complete first.
        Raises RuntimeError on model load failure so the caller can surface it early.
        """
        try:
            self._transcriber.load(progress_cb)
            can_preload = (
                self._translator is not None
                and self._config.source_lang != "auto"
            )
            if can_preload:
                self._translator.ensure_model(progress_cb)  # type: ignore[union-attr]
        except RuntimeError:
            raise

    def run(self, progress_cb: Optional[Callable[[str], None]] = None) -> PipelineResult:
        """Execute the full pipeline. Never raises — returns PipelineResult on both success and failure."""
        audio_path: Optional[str] = None
        try:
            _cb(progress_cb, "Extracting audio...")
            audio_path = extract_audio(self._config.input_path)

            _cb(progress_cb, "Transcribing...")
            segments = self._transcriber.transcribe(
                audio_path,
                language=self._config.language,
                beam_size=self._config.beam_size,
                vad_filter=self._config.vad_filter,
                progress_cb=progress_cb,
            )
            detected_lang = segments[0]["language"] if segments else ""

            translated_segs = self._translate(segments, detected_lang, progress_cb)
            output_files = self._write_outputs(segments, translated_segs, progress_cb)

            _cb(progress_cb, "Done.")
            return PipelineResult(
                success=True,
                input_path=self._config.input_path,
                segments=segments,
                translated_segments=translated_segs,
                output_files=output_files,
                detected_language=detected_lang,
            )
        except Exception as e:
            return PipelineResult(
                success=False,
                input_path=self._config.input_path,
                error=str(e),
            )
        finally:
            if audio_path:
                cleanup_temp(audio_path)

    def _translate(
        self,
        segments: list[Segment],
        detected_lang: str,
        progress_cb: Optional[Callable[[str], None]],
    ) -> list[TranslatedSegment]:
        """Run translation when enabled; resolves 'auto' source language."""
        if self._translator is None or not segments:
            return []
        try:
            _cb(progress_cb, "Translating...")
            src = detected_lang if self._config.source_lang == "auto" else self._config.source_lang
            self._translator.set_pair(src, self._config.target_lang)
            self._translator.ensure_model(progress_cb)
            return self._translator.translate_segments(segments, progress_cb)
        except Exception as e:
            raise RuntimeError(f"Translation step failed: {e}") from e

    def _write_outputs(
        self,
        segments: list[Segment],
        translated: list[TranslatedSegment],
        progress_cb: Optional[Callable[[str], None]],
    ) -> list[str]:
        """Write all requested subtitle files and return their paths."""
        out: list[str] = []
        src = self._config.input_path
        lang = self._config.target_lang

        if self._config.emit_srt:
            path = self._out_path(src, "", ".srt")
            _cb(progress_cb, f"Writing {os.path.basename(path)}...")
            write_srt(segments, path, translated=False)
            out.append(path)

        if self._config.emit_vtt:
            path = self._out_path(src, "", ".vtt")
            _cb(progress_cb, f"Writing {os.path.basename(path)}...")
            write_vtt(segments, path, translated=False)
            out.append(path)

        if translated:
            if self._config.emit_srt:
                path = self._out_path(src, f"_{lang}", ".srt")
                _cb(progress_cb, f"Writing {os.path.basename(path)}...")
                write_srt(translated, path, translated=True)
                out.append(path)
            if self._config.emit_vtt:
                path = self._out_path(src, f"_{lang}", ".vtt")
                _cb(progress_cb, f"Writing {os.path.basename(path)}...")
                write_vtt(translated, path, translated=True)
                out.append(path)

        return out

    def _out_path(self, input_path: str, suffix: str, ext: str) -> str:
        """Build an output file path, relocating to output_dir when set."""
        candidate = derive_output_path(input_path, suffix, ext)
        if self._config.output_dir:
            return os.path.join(self._config.output_dir, os.path.basename(candidate))
        return candidate


def _cb(fn: Optional[Callable[[str], None]], msg: str) -> None:
    """Call a progress callback safely when present."""
    try:
        if fn:
            fn(msg)
    except Exception:
        pass
