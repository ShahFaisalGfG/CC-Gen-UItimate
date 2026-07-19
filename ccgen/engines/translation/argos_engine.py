# argos_engine.py — argostranslate wrapper with offline model management

import logging
from typing import Callable, Optional

import argostranslate.package
import argostranslate.translate

from ccgen.config.defaults import TranslationDefaults
from ccgen.core import Segment, TranslatedSegment
from ccgen.engines.translation.base import TranslationEngine
from ccgen.utils.download_progress import download_progress

_log = logging.getLogger(__name__)


def install_pair(
    source: str,
    target: str,
    progress_num_cb: Optional[Callable[[int, int], None]] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> None:
    """Fetch the package index and install one Argos translation language pair.

    Raises RuntimeError when the pair is not present in the remote package index.
    """
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    pkg = next((p for p in available if p.from_code == source and p.to_code == target), None)
    if pkg is None:
        raise RuntimeError(f"No translation package for {source}→{target}.")
    with download_progress(progress_num_cb):
        archive_path = pkg.download()
    _cb(progress_cb, "Installing...")
    argostranslate.package.install_from_path(archive_path)


class ArgosEngine(TranslationEngine):
    """Wraps argostranslate for fully offline, segment-level translation."""

    def __init__(
        self,
        source_lang: str = TranslationDefaults.DEFAULT_SOURCE_LANG,
        target_lang: str = TranslationDefaults.DEFAULT_TARGET_LANG,
    ) -> None:
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._engine: Optional[argostranslate.translate.ITranslation] = None

    def ensure_model(
        self,
        progress_cb: Optional[Callable[[str], None]] = None,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Download and install the language pair model when not already present.

        Raises RuntimeError when the pair is unsupported or download fails.
        """
        try:
            _log.debug("ensure_model: %s→%s", self._source_lang, self._target_lang)
            if self._is_installed():
                self._engine = self._get_engine()
                _log.debug("Translation model already installed")
                return
            _cb(progress_cb, f"Downloading translation model {self._source_lang}→{self._target_lang}...")
            self._download_and_install(progress_num_cb, progress_cb)
            self._engine = self._get_engine()
            _cb(progress_cb, "Translation model ready.")
            _log.info("Translation model ready: %s→%s", self._source_lang, self._target_lang)
        except RuntimeError:
            raise
        except Exception as e:
            _log.error("Model setup failed (%s→%s): %r", self._source_lang, self._target_lang, e, exc_info=True)
            raise RuntimeError(
                f"Model setup failed ({self._source_lang}→{self._target_lang}): {e}"
            ) from e

    def translate_segments(
        self,
        segments: list[Segment],
        progress_cb: Optional[Callable[[str], None]] = None,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
        segment_cb: Optional[Callable[[TranslatedSegment], None]] = None,
    ) -> list[TranslatedSegment]:
        """Translate a segment list, preserving all timing from the source.

        Raises RuntimeError when ensure_model() has not been called first.
        """
        try:
            if self._engine is None:
                raise RuntimeError("Call ensure_model() before translate_segments().")
            _log.info("Translating %d segments (%s→%s)", len(segments), self._source_lang, self._target_lang)
            total = len(segments)
            results = [
                self._translate_one(seg, idx + 1, total, progress_cb, progress_num_cb, segment_cb)
                for idx, seg in enumerate(segments)
            ]
            _log.info("Translation complete: %d segments", len(results))
            return results
        except RuntimeError:
            raise
        except Exception as e:
            _log.error("Translation failed: %r", e, exc_info=True)
            raise RuntimeError(f"Translation failed: {e}") from e

    def set_pair(self, source: str, target: str) -> None:
        """Update the source/target language codes and reset the loaded engine."""
        self._source_lang = source
        self._target_lang = target
        self._engine = None

    def list_installed(self) -> list[str]:
        """Return installed language pair codes as 'src→tgt' strings."""
        try:
            pkgs = argostranslate.package.get_installed_packages()
            return [f"{p.from_code}→{p.to_code}" for p in pkgs]
        except Exception:
            return []

    def _is_installed(self) -> bool:
        """Return True when the required language pair package is installed."""
        try:
            pkgs = argostranslate.package.get_installed_packages()
            return any(
                p.from_code == self._source_lang and p.to_code == self._target_lang
                for p in pkgs
            )
        except Exception:
            return False

    def _download_and_install(
        self,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Fetch the package index and install the required language pair."""
        try:
            _log.info("Downloading package index for %s→%s", self._source_lang, self._target_lang)
            install_pair(self._source_lang, self._target_lang, progress_num_cb, progress_cb)
        except RuntimeError:
            raise
        except Exception as e:
            _log.error("Package download failed: %r", e, exc_info=True)
            raise RuntimeError(f"Package download failed: {e}") from e

    def _get_engine(self) -> argostranslate.translate.ITranslation:
        """Retrieve the loaded translation engine for the current language pair."""
        engine = argostranslate.translate.get_translation_from_codes(
            self._source_lang, self._target_lang
        )
        if engine is None:
            raise RuntimeError(
                f"Translation engine unavailable for {self._source_lang}→{self._target_lang}."
            )
        return engine

    def _translate_one(
        self,
        seg: Segment,
        position: int,
        total: int,
        progress_cb: Optional[Callable[[str], None]],
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
        segment_cb: Optional[Callable[[TranslatedSegment], None]] = None,
    ) -> TranslatedSegment:
        """Translate a single segment and wrap it into a TranslatedSegment."""
        text = seg["text"].strip()
        translated = self._engine.translate(text)  # type: ignore[union-attr]
        result = TranslatedSegment(
            id=seg["id"],
            start=seg["start"],
            end=seg["end"],
            original=text,
            translated=translated,
            language=self._target_lang,
        )
        _cb(progress_cb, f"Translated segment {seg['id'] + 1}")
        _seg_cb(segment_cb, result)
        _num_cb(progress_num_cb, position, total)
        return result


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


def _seg_cb(fn: Optional[Callable[[TranslatedSegment], None]], seg: TranslatedSegment) -> None:
    """Call a per-segment result callback safely when present."""
    try:
        if fn:
            fn(seg)
    except Exception:
        pass
