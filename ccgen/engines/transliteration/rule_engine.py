# rule_engine.py — fast, fully offline transliteration: indic-transliteration for genuine
# Indic-script pairs, a dedicated converter for Urdu <-> Roman Urdu, and diacritic cleanup
# for Hindi/Punjabi -> Urdu output (see urdu_roman_map.py for why the built-in scheme isn't used)

import logging
import re
from typing import Callable, Optional, Union

from indic_transliteration import sanscript

from ccgen.core import Segment, TranslatedSegment, TransliteratedSegment
from ccgen.engines.transliteration.base import TransliterationEngine
from ccgen.engines.transliteration.urdu_roman_map import roman_to_urdu, urdu_to_roman

_log = logging.getLogger(__name__)

_URDU_KEY = "ur"
_ROMAN_KEY = "roman"
_DIACRITICS_RE = re.compile("[ً-ْ]")

_INDIC_SCHEME_MAP: dict[str, str] = {
    "hi": sanscript.DEVANAGARI,
    "bn": sanscript.BENGALI,
    "gu": sanscript.GUJARATI,
    "pa": sanscript.GURMUKHI,
    "ta": sanscript.TAMIL,
    "te": sanscript.TELUGU,
    "kn": sanscript.KANNADA,
    "ml": sanscript.MALAYALAM,
    "or": sanscript.ORIYA,
    "si": "sinhala",
    "th": "thai",
    "my": "burmese",
}


class RuleEngine(TransliterationEngine):
    """Fast, fully offline transliteration using character rules and script tables."""

    def __init__(self, source_scheme: str, target_scheme: str) -> None:
        self._source_key = source_scheme
        self._target_key = target_scheme

    def set_schemes(self, source: str, target: str) -> None:
        """Update source and target scheme codes."""
        self._source_key = source
        self._target_key = target

    def transliterate_segments(
        self,
        segments: Union[list[Segment], list[TranslatedSegment]],
        progress_cb: Optional[Callable[[str], None]] = None,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
        segment_cb: Optional[Callable[[TransliteratedSegment], None]] = None,
    ) -> list[TransliteratedSegment]:
        """Transliterate a segment list between scripts, preserving timing."""
        try:
            _log.info(
                "Rule engine transliterating %d segments: %s → %s",
                len(segments), self._source_key, self._target_key,
            )
            total = len(segments)
            results = [
                self._convert_one(seg, idx + 1, total, progress_cb, progress_num_cb, segment_cb)
                for idx, seg in enumerate(segments)
            ]
            _log.info("Transliteration complete: %d segments", len(results))
            return results
        except Exception as e:
            _log.error("Transliteration failed: %r", e, exc_info=True)
            raise RuntimeError(f"Transliteration failed: {e}") from e

    def _convert_one(
        self,
        seg: Union[Segment, TranslatedSegment],
        position: int,
        total: int,
        progress_cb: Optional[Callable[[str], None]],
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
        segment_cb: Optional[Callable[[TransliteratedSegment], None]] = None,
    ) -> TransliteratedSegment:
        """Transliterate a single segment and return a TransliteratedSegment."""
        try:
            source_text: str = seg.get("translated", seg.get("text", ""))  # type: ignore[assignment,call-overload]
            converted = self._convert_text(source_text)
            result = TransliteratedSegment(
                id=seg["id"],
                start=seg["start"],
                end=seg["end"],
                original=source_text,
                transliterated=converted,
                source_scheme=self._source_key,
                target_scheme=self._target_key,
            )
            if progress_cb:
                try:
                    progress_cb(f"Transliterated segment {seg['id'] + 1}")
                except Exception:
                    pass
            _seg_cb(segment_cb, result)
            _num_cb(progress_num_cb, position, total)
            return result
        except Exception as e:
            _log.error("Segment %s transliteration error: %r", seg.get("id", "?"), e, exc_info=True)  # type: ignore[call-overload]
            raise RuntimeError(f"Segment {seg.get('id', '?')} transliteration error: {e}") from e  # type: ignore[call-overload]

    def _convert_text(self, text: str) -> str:
        """Route text through the dedicated Urdu<->Roman converter or sanscript, as appropriate."""
        if self._source_key == _URDU_KEY and self._target_key == _ROMAN_KEY:
            return urdu_to_roman(text)
        if self._source_key == _ROMAN_KEY and self._target_key == _URDU_KEY:
            return roman_to_urdu(text)
        source = self._resolve(self._source_key)
        target = self._resolve(self._target_key)
        converted = sanscript.transliterate(text, source, target)
        if self._target_key == _URDU_KEY:
            converted = strip_diacritics(converted)
        return converted

    def _resolve(self, key: str) -> str:
        """Map a user-facing scheme key to an indic-transliteration scheme constant."""
        if key == _URDU_KEY:
            return "urdu"
        if key == _ROMAN_KEY:
            return sanscript.IAST
        resolved = _INDIC_SCHEME_MAP.get(key)
        if resolved is None:
            raise ValueError(f"Unknown transliteration scheme: '{key}'.")
        return resolved


def strip_diacritics(text: str) -> str:
    """Remove Arabic short-vowel diacritics that real Urdu writing normally omits."""
    return _DIACRITICS_RE.sub("", text)


def _num_cb(fn: Optional[Callable[[int, int], None]], done: int, total: int) -> None:
    """Call a numeric progress callback safely when present."""
    try:
        if fn:
            fn(done, total)
    except Exception:
        pass


def _seg_cb(fn: Optional[Callable[[TransliteratedSegment], None]], seg: TransliteratedSegment) -> None:
    """Call a per-segment result callback safely when present."""
    try:
        if fn:
            fn(seg)
    except Exception:
        pass
