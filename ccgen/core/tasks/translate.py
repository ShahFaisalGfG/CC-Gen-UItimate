# translate.py - translate subtitle cues into another language
#
# Cues are often half-sentence fragments; translating them one by one loses the context a
# sentence-level model needs, especially between languages with different word order (e.g.
# English to Urdu). Whole sentences are translated, then spread back over their cues.

import logging
import os

from ccgen.config.capabilities import language_from_filename
from ccgen.core import Segment, TranslatedSegment
from ccgen.core.cues import CueLayout, join_unit_text, sentence_units, spread_translation
from ccgen.core.subtitle_parser import parse_subtitle
from ccgen.core.tasks.base import RunContext, Task, TaskResult, Track
from ccgen.core.tasks.configs import TranslateConfig
from ccgen.core.tasks.outputs import write_track
from ccgen.engines.translation import create_engine as create_translation_engine
from ccgen.engines.translation.base import TranslationEngine
from ccgen.utils.callbacks import JobCancelled

_log = logging.getLogger(__name__)


def load_subtitle_track(path: str, language: str = "") -> Track:
    """Parse a subtitle file into a track, taking its language from `language` or the file name."""
    language = language or language_from_filename(path)
    cues = parse_subtitle(path)
    for cue in cues:
        cue["language"] = language
    return Track(cues=cues, language=language)


def resolve_source(requested: str, track: Track, input_path: str) -> str:
    """Return the explicit source language, or the track's own language for "auto"."""
    if requested != "auto":
        return requested
    if track.language:
        return track.language
    raise ValueError(
        f"Can't tell which language {os.path.basename(input_path)} is in. Choose the source language, "
        "or name the file with a language suffix such as movie_en.srt."
    )


def translate_track(
    track: Track,
    engine: TranslationEngine,
    source: str,
    target: str,
    ctx: RunContext,
) -> Track:
    """Translate whole sentences of `track`, then spread each translation back over its cues."""
    if source == target:
        raise ValueError(f"The subtitles are already in '{target}'. Choose a different target language.")
    cues = track.cues
    if not cues:
        return Track(cues=[], language=target)
    units = sentence_units(cues)
    unit_segments = [
        Segment(
            id=idx,
            start=cues[members[0]]["start"],
            end=cues[members[-1]]["end"],
            text=join_unit_text([cues[i] for i in members], source),
            words=[],
            language=source,
        )
        for idx, members in enumerate(units)
    ]

    def spread(unit: TranslatedSegment) -> list[TranslatedSegment]:
        return spread_translation([cues[i] for i in units[unit["id"]]], unit["translated"], target)

    def on_unit(unit: TranslatedSegment) -> None:
        for part in spread(unit):
            ctx.segment(part)

    _log.debug("Translating %d sentences (%d cues): %s → %s", len(units), len(cues), source, target)
    try:
        engine.set_pair(source, target)
        engine.ensure_model(ctx.status, ctx.progress)
        translated_units = engine.translate_segments(unit_segments, ctx.status, ctx.progress, on_unit)
    except JobCancelled:
        raise
    except Exception as e:
        _log.error("Translation failed: %r", e, exc_info=True)
        raise RuntimeError(f"Translation failed: {e}") from e
    parts = [part for unit in translated_units for part in spread(unit)]
    return Track(
        cues=[
            Segment(id=p["id"], start=p["start"], end=p["end"], text=p["translated"], words=[], language=target)
            for p in parts
        ],
        language=target,
    )


class TranslateTask(Task[TranslateConfig]):
    """Translate one subtitle file and write the translated subtitles."""

    def __init__(self, config: TranslateConfig) -> None:
        super().__init__(config)
        self._layout = CueLayout(max_line_length=config.max_line_length, max_lines=config.max_lines)
        self._engine = create_translation_engine(source_lang=config.source_lang, target_lang=config.target_lang)

    @property
    def stages(self) -> list[str]:
        """Translation only; the language model is installed as part of it."""
        return ["translate"]

    def _run(self, ctx: RunContext) -> TaskResult:
        cfg = self.config
        ctx.begin("translate", "Reading subtitle file...")
        track = load_subtitle_track(cfg.input_path)
        for cue in track.cues:
            ctx.segment(cue)
        source = resolve_source(cfg.source_lang, track, cfg.input_path)
        ctx.status("Translating...")
        translated = translate_track(track, self._engine, source, cfg.target_lang, ctx)
        ctx.status("Writing subtitle files...")
        files = write_track(
            translated, cfg.input_path, f"_{cfg.target_lang}", cfg.formats, self._layout, cfg.output_dir,
        )
        return TaskResult(
            success=True, input_path=cfg.input_path, output_files=files,
            detected_language=source, output_languages=dict.fromkeys(files, cfg.target_lang),
        )
