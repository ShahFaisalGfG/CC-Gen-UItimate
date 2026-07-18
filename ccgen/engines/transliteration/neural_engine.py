# neural_engine.py — higher-quality transliteration via small local neural models,
# auto-downloaded once and cached offline thereafter (same pattern as ArgosEngine).
#
# Urdu <-> Roman Urdu: Mavkif's m2m100 fine-tune (standard transformers format, Apache-2.0).
# Hindi -> Urdu: rekhtalabs' vendored character-Transformer checkpoint (see rekhta_backend.py).
# Punjabi -> Urdu: pivots through Devanagari (Gurmukhi -> Devanagari via indic-transliteration,
# then the Hindi -> Urdu model), since no direct Punjabi -> Urdu neural model exists.

import logging
from typing import Callable, Optional, Union

import torch
from indic_transliteration import sanscript
from transformers import AutoTokenizer, M2M100ForConditionalGeneration, PreTrainedTokenizerBase

from ccgen.core import Segment, TranslatedSegment, TransliteratedSegment
from ccgen.engines.transliteration.base import TransliterationEngine
from ccgen.engines.transliteration.rekhta_backend import RekhtaBackend
from ccgen.utils.download_progress import download_progress

_log = logging.getLogger(__name__)

_TOKENIZER_MODEL = "Mavkif/m2m100_rup_tokenizer_both"
_M2M100_MODELS: dict[tuple[str, str], str] = {
    ("ur", "roman"): "Mavkif/m2m100_rup_ur_to_rur",
    ("roman", "ur"): "Mavkif/m2m100_rup_rur_to_ur",
}
_LANG_TOKENS: dict[str, str] = {"ur": "__ur__", "roman": "__roman-ur__"}
_MAX_NEW_TOKENS = 256


class NeuralEngine(TransliterationEngine):
    """Higher-quality transliteration using small local neural models."""

    def __init__(self, source_scheme: str, target_scheme: str) -> None:
        self._source_key = source_scheme
        self._target_key = target_scheme
        self._m2m_tokenizer: Optional[PreTrainedTokenizerBase] = None
        self._m2m_model: Optional[M2M100ForConditionalGeneration] = None
        self._rekhta = RekhtaBackend()
        self._rekhta_loaded = False

    def set_schemes(self, source: str, target: str) -> None:
        """Update source and target scheme codes."""
        self._source_key = source
        self._target_key = target

    def transliterate_segments(
        self,
        segments: Union[list[Segment], list[TranslatedSegment]],
        progress_cb: Optional[Callable[[str], None]] = None,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
    ) -> list[TransliteratedSegment]:
        """Transliterate a segment list between scripts, preserving timing."""
        try:
            _log.info(
                "Neural engine transliterating %d segments: %s → %s",
                len(segments), self._source_key, self._target_key,
            )
            self._ensure_loaded(progress_cb, progress_num_cb)
            total = len(segments)
            results = [
                self._convert_one(seg, idx + 1, total, progress_cb, progress_num_cb)
                for idx, seg in enumerate(segments)
            ]
            _log.info("Transliteration complete: %d segments", len(results))
            return results
        except Exception as e:
            _log.error("Neural transliteration failed: %r", e, exc_info=True)
            raise RuntimeError(f"Neural transliteration failed: {e}") from e

    def _ensure_loaded(
        self,
        progress_cb: Optional[Callable[[str], None]],
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Load whichever backend the current scheme pair needs, once."""
        pair = (self._source_key, self._target_key)
        if pair in _M2M100_MODELS:
            if self._m2m_model is None:
                self._load_m2m100(pair, progress_cb, progress_num_cb)
            return
        if self._source_key in ("hi", "pa") and self._target_key == "ur":
            if not self._rekhta_loaded:
                self._rekhta.load(progress_cb, progress_num_cb)
                self._rekhta_loaded = True
            return
        raise ValueError(f"No neural engine available for {self._source_key} → {self._target_key}")

    def _load_m2m100(
        self,
        pair: tuple[str, str],
        progress_cb: Optional[Callable[[str], None]],
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Download and load the Mavkif m2m100 fine-tune for one Urdu<->Roman direction."""
        model_id = _M2M100_MODELS[pair]
        _cb(progress_cb, f"Downloading neural transliteration model ({model_id})...")
        with download_progress(progress_num_cb):
            self._m2m_tokenizer = AutoTokenizer.from_pretrained(_TOKENIZER_MODEL)
            self._m2m_model = M2M100ForConditionalGeneration.from_pretrained(model_id)
        self._m2m_model.eval()
        _cb(progress_cb, "Neural transliteration model ready.")

    def _convert_one(
        self,
        seg: Union[Segment, TranslatedSegment],
        position: int,
        total: int,
        progress_cb: Optional[Callable[[str], None]],
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
    ) -> TransliteratedSegment:
        """Transliterate a single segment and return a TransliteratedSegment."""
        try:
            source_text: str = seg.get("translated", seg.get("text", ""))  # type: ignore[assignment,call-overload]
            converted = self._convert_text(source_text)
            if progress_cb:
                try:
                    progress_cb(f"Transliterated segment {seg['id'] + 1}")
                except Exception:
                    pass
            _num_cb(progress_num_cb, position, total)
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

    def _convert_text(self, text: str) -> str:
        """Route text to the loaded backend for the current scheme pair."""
        pair = (self._source_key, self._target_key)
        if pair in _M2M100_MODELS:
            return self._m2m100_translate(text)
        if self._source_key == "pa":
            devanagari = sanscript.transliterate(text, sanscript.GURMUKHI, sanscript.DEVANAGARI)
            return self._rekhta.convert(devanagari)
        return self._rekhta.convert(text)

    def _m2m100_translate(self, text: str) -> str:
        """Run one string through the loaded Mavkif m2m100 model.

        The tokenizer's built-in language list doesn't include "roman-ur", so the source/target
        language tokens are resolved and prepended manually rather than via tokenizer.src_lang.
        """
        assert self._m2m_tokenizer is not None and self._m2m_model is not None
        src_id = self._m2m_tokenizer.convert_tokens_to_ids(_LANG_TOKENS[self._source_key])
        tgt_id = self._m2m_tokenizer.convert_tokens_to_ids(_LANG_TOKENS[self._target_key])
        body_ids = self._m2m_tokenizer(text, add_special_tokens=False)["input_ids"]
        input_ids = torch.tensor([[src_id] + body_ids + [self._m2m_tokenizer.eos_token_id]])
        with torch.no_grad():
            generated = self._m2m_model.generate(  # type: ignore[reportAttributeAccessIssue]
                input_ids, forced_bos_token_id=tgt_id, max_new_tokens=_MAX_NEW_TOKENS,
            )
        decoded = self._m2m_tokenizer.decode(generated[0], skip_special_tokens=True)
        return decoded if isinstance(decoded, str) else str(decoded)


def _cb(fn: Optional[Callable[[str], None]], msg: str) -> None:
    """Call a progress callback safely when present."""
    try:
        if fn:
            fn(msg)
    except Exception:
        pass


def _num_cb(fn: Optional[Callable[[int, int], None]], done: int, total: int) -> None:
    """Call a numeric progress callback safely when present."""
    try:
        if fn:
            fn(done, total)
    except Exception:
        pass
