# model_status.py — checks whether a model/engine/language asset is already cached locally,
# so the settings UI can show a downloaded vs needs-download indicator without any network call.

import logging

import argostranslate.package
from huggingface_hub import scan_cache_dir

_log = logging.getLogger(__name__)

_WHISPER_REPOS: dict[str, str] = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}

_NEURAL_TOKENIZER_REPO = "Mavkif/m2m100_rup_tokenizer_both"
_NEURAL_MODEL_REPOS: dict[tuple[str, str], str] = {
    ("ur", "roman"): "Mavkif/m2m100_rup_ur_to_rur",
    ("roman", "ur"): "Mavkif/m2m100_rup_rur_to_ur",
}
_REKHTA_REPO = "rekhtalabs/hi-2-ur-translit"


def whisper_cached(model_name: str) -> bool:
    """Return True when the given Whisper model is already cached locally."""
    repo_id = _WHISPER_REPOS.get(model_name)
    if repo_id is None:
        return False
    return _repo_cached(repo_id)


def neural_translit_cached(source: str, target: str) -> bool:
    """Return True when the neural transliteration backend for this pair is already cached."""
    pair = (source, target)
    if pair in _NEURAL_MODEL_REPOS:
        return _repo_cached(_NEURAL_MODEL_REPOS[pair]) and _repo_cached(_NEURAL_TOKENIZER_REPO)
    if source in ("hi", "pa") and target == "ur":
        return _repo_cached(_REKHTA_REPO)
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


def _repo_cached(repo_id: str) -> bool:
    """Return True when any revision of `repo_id` is present in the local Hugging Face cache."""
    try:
        cache_info = scan_cache_dir()
        return any(repo.repo_id == repo_id for repo in cache_info.repos)
    except Exception:
        _log.debug("Failed to scan Hugging Face cache", exc_info=True)
        return False
