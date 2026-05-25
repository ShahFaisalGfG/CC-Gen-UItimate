# transliterator.py — phonetic script conversion using indic-transliteration

import logging
from typing import Callable, Optional, Union

from indic_transliteration import sanscript

from ccgen.core import Segment, TranslatedSegment, TransliteratedSegment

_log = logging.getLogger(__name__)

_SCHEME_MAP: dict[str, str] = {
    "roman": sanscript.IAST,
    "ur":    "urdu",
    "hi":    sanscript.DEVANAGARI,
    "bn":    sanscript.BENGALI,
    "gu":    sanscript.GUJARATI,
    "pa":    sanscript.GURMUKHI,
    "ta":    sanscript.TAMIL,
    "te":    sanscript.TELUGU,
    "kn":    sanscript.KANNADA,
    "ml":    sanscript.MALAYALAM,
    "or":    sanscript.ORIYA,
    "si":    "sinhala",
    "th":    "thai",
    "my":    "burmese",
}


class Transliterator:
    """Converts text phonetically between writing scripts, preserving segment timing."""

    SCHEME_MAP: dict[str, str] = _SCHEME_MAP

    def __init__(self, source_scheme: str, target_scheme: str) -> None:
        self._source = self._resolve(source_scheme)
        self._target = self._resolve(target_scheme)
        self._source_key = source_scheme
        self._target_key = target_scheme

    def set_schemes(self, source: str, target: str) -> None:
        """Update source and target scheme codes."""
        self._source = self._resolve(source)
        self._target = self._resolve(target)
        self._source_key = source
        self._target_key = target

    def transliterate_segments(
        self,
        segments: Union[list[Segment], list[TranslatedSegment]],
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> list[TransliteratedSegment]:
        """Transliterate a segment list between scripts, preserving timing."""
        try:
            _log.info(
                "Transliterating %d segments: %s → %s",
                len(segments), self._source_key, self._target_key,
            )
            results: list[TransliteratedSegment] = []
            for seg in segments:
                results.append(self._convert_one(seg, progress_cb))
            _log.info("Transliteration complete: %d segments", len(results))
            return results
        except Exception as e:
            _log.error("Transliteration failed: %r", e, exc_info=True)
            raise RuntimeError(f"Transliteration failed: {e}") from e

    def _convert_one(
        self,
        seg: Union[Segment, TranslatedSegment],
        progress_cb: Optional[Callable[[str], None]],
    ) -> TransliteratedSegment:
        """Transliterate a single segment and return a TransliteratedSegment."""
        try:
            source_text: str = seg.get("translated", seg.get("text", ""))  # type: ignore[assignment,call-overload]
            converted = sanscript.transliterate(source_text, self._source, self._target)
            if progress_cb:
                try:
                    progress_cb(f"Transliterated segment {seg['id'] + 1}")
                except Exception:
                    pass
            return TransliteratedSegment(
                id=seg["id"],
                start=seg["start"],
                end=seg["end"],
                original=source_text,
                transliterated=converted,
                source_scheme=self._source_key,
                target_scheme=self._target_key,
            )
        except Exception as e:
            _log.error("Segment %s transliteration error: %r", seg.get("id", "?"), e, exc_info=True)  # type: ignore[call-overload]
            raise RuntimeError(f"Segment {seg.get('id', '?')} transliteration error: {e}") from e  # type: ignore[call-overload]

    def _resolve(self, key: str) -> str:
        """Map a user-facing scheme key to an indic-transliteration scheme constant."""
        resolved = self.SCHEME_MAP.get(key)
        if resolved is None:
            raise ValueError(
                f"Unknown transliteration scheme: '{key}'. Supported: {list(self.SCHEME_MAP)}"
            )
        return resolved
