# argos_engine.py - argostranslate wrapper with offline model management

import logging
from typing import Any, Callable, Optional

import argostranslate.package
import argostranslate.translate

from ccgen.config.defaults import TranslationDefaults
from ccgen.core import Segment, TranslatedSegment
from ccgen.engines.translation.base import TranslationEngine
from ccgen.utils.callbacks import JobCancelled, emit_progress, emit_segment, emit_status
from ccgen.utils.download_progress import download_progress

_log = logging.getLogger(__name__)

# Argos publishes most language pairs only to and from English, and chains two installed
# packages through a shared language automatically, so English is the pivot for other pairs.
_PIVOT_LANG = "en"


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
    pkg = _find_package(available, source, target)
    if pkg is None:
        raise RuntimeError(f"No translation package for {source}→{target}.")
    _install_package(pkg, progress_num_cb, progress_cb)


def install_route(
    source: str,
    target: str,
    progress_num_cb: Optional[Callable[[int, int], None]] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> None:
    """Install whatever packages translating source→target needs.

    Uses the direct pair when Argos publishes one, otherwise the two legs through English
    (e.g. Urdu→French installs ur→en and en→fr). Raises RuntimeError when neither route exists.
    """
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    direct = _find_package(available, source, target)
    if direct is not None:
        _install_package(direct, progress_num_cb, progress_cb)
        return
    if _PIVOT_LANG in (source, target):
        raise RuntimeError(f"No translation package for {source}→{target}.")
    installed = argostranslate.package.get_installed_packages()
    for leg_source, leg_target in ((source, _PIVOT_LANG), (_PIVOT_LANG, target)):
        if _find_package(installed, leg_source, leg_target) is not None:
            continue
        leg = _find_package(available, leg_source, leg_target)
        if leg is None:
            raise RuntimeError(f"No translation package for {source}→{target}.")
        _install_package(leg, progress_num_cb, progress_cb)


def _find_package(packages: list, source: str, target: str) -> Optional[Any]:
    """Return the package translating source→target from a package list, if any."""
    return next((p for p in packages if p.from_code == source and p.to_code == target), None)


def _install_package(
    pkg: Any,
    progress_num_cb: Optional[Callable[[int, int], None]],
    progress_cb: Optional[Callable[[str], None]],
) -> None:
    """Download one Argos package with byte progress, then install it."""
    with download_progress(progress_num_cb):
        archive_path = pkg.download()
    emit_status(progress_cb, "Installing...")
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
            emit_status(progress_cb, f"Downloading translation model {self._source_lang}→{self._target_lang}...")
            self._download_and_install(progress_num_cb, progress_cb)
            self._engine = self._get_engine()
            emit_status(progress_cb, "Translation model ready.")
            _log.info("Translation model ready: %s→%s", self._source_lang, self._target_lang)
        except (RuntimeError, JobCancelled):
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
                self._translate_one(seg, idx + 1, total, progress_num_cb, segment_cb)
                for idx, seg in enumerate(segments)
            ]
            _log.info("Translation complete: %d segments", len(results))
            return results
        except (RuntimeError, JobCancelled):
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
        """Return True when the pair is installed directly or through both English legs."""
        try:
            pkgs = argostranslate.package.get_installed_packages()
            source, target = self._source_lang, self._target_lang
            if _find_package(pkgs, source, target) is not None:
                return True
            return (
                _PIVOT_LANG not in (source, target)
                and _find_package(pkgs, source, _PIVOT_LANG) is not None
                and _find_package(pkgs, _PIVOT_LANG, target) is not None
            )
        except Exception:
            _log.debug("Failed to read installed translation packages", exc_info=True)
            return False

    def _download_and_install(
        self,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Fetch the package index and install the packages this pair needs."""
        try:
            _log.info("Downloading package index for %s→%s", self._source_lang, self._target_lang)
            install_route(self._source_lang, self._target_lang, progress_num_cb, progress_cb)
        except (RuntimeError, JobCancelled):
            raise
        except Exception as e:
            _log.error("Package download failed: %r", e, exc_info=True)
            raise RuntimeError(f"Package download failed: {e}") from e

    def _get_engine(self) -> argostranslate.translate.ITranslation:
        """Retrieve the loaded translation engine (direct or pivoted) for the current pair."""
        try:
            engine = argostranslate.translate.get_translation_from_codes(
                self._source_lang, self._target_lang
            )
        except AttributeError:
            # get_translation_from_codes dereferences None when a language isn't installed.
            engine = None
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
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
        segment_cb: Optional[Callable[[TranslatedSegment], None]] = None,
    ) -> TranslatedSegment:
        """Translate a single segment and wrap it into a TranslatedSegment."""
        text = seg["text"].strip()
        translated = self._engine.translate(text).strip() if text else ""  # type: ignore[union-attr]
        result = TranslatedSegment(
            id=seg["id"],
            start=seg["start"],
            end=seg["end"],
            original=text,
            translated=translated,
            language=self._target_lang,
        )
        emit_segment(segment_cb, result)
        emit_progress(progress_num_cb, position, total)
        return result
