# model_status.py - checks whether a model/engine/language asset is already cached locally,
# so the settings UI can show a downloaded vs needs-download indicator without any network call.

import logging
from pathlib import Path
from typing import Any, Optional

import argostranslate.package
from huggingface_hub import scan_cache_dir

from ccgen.config.defaults import ModelRepos

_log = logging.getLogger(__name__)


def scan_hf_cache() -> Optional[Any]:
    """Scan the local Hugging Face cache once; returns None when the scan fails.

    Pass the result to the *_cached() helpers when checking several models in a row, since
    each scan walks the whole cache directory.
    """
    try:
        return scan_cache_dir()
    except Exception:
        _log.debug("Failed to scan Hugging Face cache", exc_info=True)
        return None


def whisper_cached(model_name: str, cache_info: Optional[Any] = None) -> bool:
    """Return True when the given Whisper model is already cached locally."""
    repo_id = ModelRepos.WHISPER.get(model_name)
    if repo_id is None:
        return False
    return _repo_cached(repo_id, cache_info)


def neural_translit_cached(source: str, target: str, cache_info: Optional[Any] = None) -> bool:
    """Return True when the neural transliteration backend for this pair is already cached."""
    pair = (source, target)
    if pair in ModelRepos.M2M100:
        cache_info = cache_info if cache_info is not None else scan_hf_cache()
        return (
            _repo_cached(ModelRepos.M2M100[pair], cache_info)
            and _repo_cached(ModelRepos.M2M100_TOKENIZER, cache_info)
        )
    if source in ("hi", "pa") and target == "ur":
        return _repo_cached(ModelRepos.REKHTA, cache_info)
    return False


def translation_pair_cached(source: str, target: str) -> bool:
    """Return True when an installed argos package already covers this language pair.

    An empty/unknown `source` (e.g. Auto-detect) falls back to checking any installed
    package that targets `target`, since the real source is only known at run time.
    """
    try:
        installed = argostranslate.package.get_installed_packages()
        if source:
            return any(p.from_code == source and p.to_code == target for p in installed)
        return any(p.to_code == target for p in installed)
    except Exception:
        _log.debug("Failed to read installed translation packages", exc_info=True)
        return False


def _repo_cached(repo_id: str, cache_info: Optional[Any] = None) -> bool:
    """Return True when `repo_id` is fully present in the local Hugging Face cache.

    A repo interrupted mid-download (app crash, force-close) leaves its small metadata
    files resolved but its large weight file as a stray `.incomplete` blob with no
    snapshot symlink - scan_cache_dir() still lists that repo, so completeness also
    requires no leftover `.incomplete` blob anywhere under it.
    """
    try:
        if cache_info is None:
            cache_info = scan_cache_dir()
        for repo in cache_info.repos:
            if repo.repo_id == repo_id:
                return not any(Path(repo.repo_path, "blobs").glob("*.incomplete"))
        return False
    except Exception:
        _log.debug("Failed to scan Hugging Face cache", exc_info=True)
        return False
