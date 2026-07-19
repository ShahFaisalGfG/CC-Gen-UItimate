# asset_registry.py — catalog of every downloadable model/engine/language asset, plus the
# blocking download/delete actions the "Manage Models" screen drives through asset_manager.py

import logging
from pathlib import Path
from typing import Callable, Optional, TypedDict

import argostranslate.package
from faster_whisper import WhisperModel
from huggingface_hub import scan_cache_dir

from ccgen.config.defaults import LanguageOptions, ModelDefaults
from ccgen.engines.transliteration.neural_engine import NeuralEngine
from ccgen.engines.transliteration.rekhta_backend import RekhtaBackend
from ccgen.engines.translation.argos_engine import install_pair
from ccgen.utils import model_status
from ccgen.utils.download_progress import cancellable, download_progress

_log = logging.getLogger(__name__)

CATEGORY_WHISPER = "whisper"
CATEGORY_TRANSLATION = "translation"
CATEGORY_TRANSLITERATION = "transliteration"

# Engine names shown as sub-groups within each category tab in Manage Models - each
# category has exactly one engine today, but is expected to grow more over time.
ENGINE_FASTER_WHISPER = "Faster Whisper"
ENGINE_ARGOS_TRANSLATE = "Argos Translate"
ENGINE_NEURAL_M2M100 = "Neural (M2M100)"
ENGINE_NEURAL_REKHTA = "Neural (Rekhta)"

_TRANSLATION_SOURCE = "en"

# Repo ids duplicated from model_status.py by design — that module keeps its own copy for
# cache-status checks only, this one for size/download/delete; neither imports the other's.
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

# Approximate sizes for not-yet-downloaded assets, in MB. Unlike Whisper's well-published
# sizes, Argos and these vendored repos expose no size field for uninstalled packages, so
# these are measured directly from each repo's Hugging Face file metadata (or, for Argos,
# from a real installed package) rather than guessed.
_TRANSLATION_APPROX_SIZES_MB: dict[str, int] = {
    "ar": 92, "fr": 79, "de": 157, "hi": 112, "pt": 79,
    "ru": 207, "es": 92, "tr": 129, "ur": 80,
}
_TRANSLIT_APPROX_SIZES_MB: dict[str, int] = {
    "roman-ur": 1856, "ur-roman": 1856, "hi-ur": 47,
}


class AssetInfo(TypedDict):
    """One row in the Manage Models catalog."""

    id: str
    category: str
    engine: str
    label: str
    downloaded: bool
    size_bytes: Optional[int]
    approx_size_mb: Optional[int]


def list_assets() -> list[AssetInfo]:
    """Build the full catalog of downloadable assets with their current cached state."""
    return _whisper_assets() + _translation_assets() + _transliteration_assets()


def download_asset(
    asset_id: str,
    progress_cb: Optional[Callable[[str], None]] = None,
    progress_num_cb: Optional[Callable[[int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> None:
    """Download one catalog asset by id. Raises RuntimeError on failure."""
    try:
        category, key = _split_id(asset_id)
        # Sent before any category-specific work so the UI leaves "Queued" the moment the
        # worker actually starts, rather than waiting on a first byte-progress tick that some
        # download paths (large multi-file Hugging Face repos in particular) may report late
        # or not at all.
        _cb(progress_cb, "Downloading...")
        with cancellable(cancel_check):
            if category == CATEGORY_WHISPER:
                _download_whisper(key, progress_num_cb)
            elif category == CATEGORY_TRANSLATION:
                install_pair(_TRANSLATION_SOURCE, key, progress_num_cb, progress_cb)
            elif category == CATEGORY_TRANSLITERATION:
                _download_transliteration(key, progress_cb, progress_num_cb)
            else:
                raise ValueError(f"Unknown asset id: {asset_id}")
    except RuntimeError:
        raise
    except Exception as e:
        _log.error("Asset download failed (%s): %r", asset_id, e, exc_info=True)
        raise RuntimeError(f"Download failed: {e}") from e


def delete_asset(asset_id: str) -> None:
    """Remove one downloaded catalog asset from local storage. Raises RuntimeError on failure."""
    try:
        category, key = _split_id(asset_id)
        if category == CATEGORY_WHISPER:
            _delete_hf_repo(_WHISPER_REPOS[key])
        elif category == CATEGORY_TRANSLATION:
            _delete_translation_pair(_TRANSLATION_SOURCE, key)
        elif category == CATEGORY_TRANSLITERATION:
            _delete_transliteration(key)
        else:
            raise ValueError(f"Unknown asset id: {asset_id}")
    except Exception as e:
        _log.error("Asset delete failed (%s): %r", asset_id, e, exc_info=True)
        raise RuntimeError(f"Remove failed: {e}") from e


def _whisper_assets() -> list[AssetInfo]:
    """Build the Whisper Models category rows."""
    assets: list[AssetInfo] = []
    for name in ModelDefaults.SUPPORTED_MODELS:
        downloaded = model_status.whisper_cached(name)
        assets.append(AssetInfo(
            id=f"{CATEGORY_WHISPER}:{name}",
            category=CATEGORY_WHISPER,
            engine=ENGINE_FASTER_WHISPER,
            label=name,
            downloaded=downloaded,
            size_bytes=_hf_repo_size(_WHISPER_REPOS[name]) if downloaded else None,
            approx_size_mb=ModelDefaults.MODEL_SIZES_MB.get(name),
        ))
    return assets


def _translation_assets() -> list[AssetInfo]:
    """Build the Translation Languages category rows (English → each other supported target)."""
    assets: list[AssetInfo] = []
    for name, code in LanguageOptions.TRANSLATION_TARGETS:
        if code == _TRANSLATION_SOURCE:
            continue  # "English → English" isn't a real, installable pair
        downloaded = model_status.translation_pair_cached(_TRANSLATION_SOURCE, code)
        assets.append(AssetInfo(
            id=f"{CATEGORY_TRANSLATION}:{code}",
            category=CATEGORY_TRANSLATION,
            engine=ENGINE_ARGOS_TRANSLATE,
            label=f"English → {name}",
            downloaded=downloaded,
            size_bytes=_installed_pair_size(_TRANSLATION_SOURCE, code) if downloaded else None,
            approx_size_mb=_TRANSLATION_APPROX_SIZES_MB.get(code),
        ))
    return assets


def _transliteration_assets() -> list[AssetInfo]:
    """Build the Transliteration Models category rows."""
    assets: list[AssetInfo] = []
    for key, pair, label in (
        ("roman-ur", ("roman", "ur"), "Roman → Urdu"),
        ("ur-roman", ("ur", "roman"), "Urdu → Roman"),
    ):
        downloaded = model_status.neural_translit_cached(*pair)
        assets.append(AssetInfo(
            id=f"{CATEGORY_TRANSLITERATION}:{key}",
            category=CATEGORY_TRANSLITERATION,
            engine=ENGINE_NEURAL_M2M100,
            label=label,
            downloaded=downloaded,
            size_bytes=_translit_pair_size(_NEURAL_MODEL_REPOS[pair]) if downloaded else None,
            approx_size_mb=_TRANSLIT_APPROX_SIZES_MB.get(key),
        ))
    rekhta_downloaded = model_status.neural_translit_cached("hi", "ur")
    assets.append(AssetInfo(
        id=f"{CATEGORY_TRANSLITERATION}:hi-ur",
        category=CATEGORY_TRANSLITERATION,
        engine=ENGINE_NEURAL_REKHTA,
        label="Hindi/Punjabi → Urdu",
        downloaded=rekhta_downloaded,
        size_bytes=_hf_repo_size(_REKHTA_REPO) if rekhta_downloaded else None,
        approx_size_mb=_TRANSLIT_APPROX_SIZES_MB.get("hi-ur"),
    ))
    return assets


def _download_whisper(model_name: str, progress_num_cb: Optional[Callable[[int, int], None]]) -> None:
    """Trigger a faster-whisper model download by instantiating it once."""
    with download_progress(progress_num_cb):
        WhisperModel(model_name, device="cpu", compute_type="int8")


def _download_transliteration(
    key: str,
    progress_cb: Optional[Callable[[str], None]],
    progress_num_cb: Optional[Callable[[int, int], None]],
) -> None:
    """Download one transliteration asset: an M2M100 direction pair or the Rekhta model."""
    if key == "roman-ur":
        NeuralEngine("roman", "ur").ensure_loaded(progress_cb, progress_num_cb)
    elif key == "ur-roman":
        NeuralEngine("ur", "roman").ensure_loaded(progress_cb, progress_num_cb)
    elif key == "hi-ur":
        RekhtaBackend().load(progress_cb, progress_num_cb)
    else:
        raise ValueError(f"Unknown transliteration asset: {key}")


def _delete_transliteration(key: str) -> None:
    """Delete one transliteration asset's model repo (the shared tokenizer is left in place)."""
    if key == "roman-ur":
        _delete_hf_repo(_NEURAL_MODEL_REPOS[("roman", "ur")])
    elif key == "ur-roman":
        _delete_hf_repo(_NEURAL_MODEL_REPOS[("ur", "roman")])
    elif key == "hi-ur":
        _delete_hf_repo(_REKHTA_REPO)
    else:
        raise ValueError(f"Unknown transliteration asset: {key}")


def _delete_hf_repo(repo_id: str) -> None:
    """Delete every cached revision of one Hugging Face repo, if present."""
    cache_info = scan_cache_dir()
    repo = next((r for r in cache_info.repos if r.repo_id == repo_id), None)
    if repo is None:
        return
    hashes = [rev.commit_hash for rev in repo.revisions]
    cache_info.delete_revisions(*hashes).execute()


def _delete_translation_pair(source: str, target: str) -> None:
    """Uninstall the Argos package for one language pair, if installed."""
    installed = argostranslate.package.get_installed_packages()
    pkg = next((p for p in installed if p.from_code == source and p.to_code == target), None)
    if pkg is not None:
        argostranslate.package.uninstall(pkg)


def _hf_repo_size(repo_id: str) -> Optional[int]:
    """Return the on-disk size of a cached Hugging Face repo, or None when not cached."""
    try:
        cache_info = scan_cache_dir()
        repo = next((r for r in cache_info.repos if r.repo_id == repo_id), None)
        return repo.size_on_disk if repo else None
    except Exception:
        _log.debug("Failed to size Hugging Face repo %s", repo_id, exc_info=True)
        return None


def _translit_pair_size(model_repo: str) -> Optional[int]:
    """Return the combined size of an M2M100 direction repo plus the shared tokenizer repo."""
    model_size = _hf_repo_size(model_repo)
    if model_size is None:
        return None
    return model_size + (_hf_repo_size(_NEURAL_TOKENIZER_REPO) or 0)


def _installed_pair_size(source: str, target: str) -> Optional[int]:
    """Return the on-disk size of an installed Argos package, or None when not installed."""
    try:
        installed = argostranslate.package.get_installed_packages()
        pkg = next((p for p in installed if p.from_code == source and p.to_code == target), None)
        if pkg is None:
            return None
        return sum(f.stat().st_size for f in Path(pkg.package_path).rglob("*") if f.is_file())
    except Exception:
        _log.debug("Failed to size Argos package %s→%s", source, target, exc_info=True)
        return None


def _split_id(asset_id: str) -> tuple[str, str]:
    """Split an asset id like 'whisper:tiny' into (category, key)."""
    category, _, key = asset_id.partition(":")
    return category, key


def _cb(fn: Optional[Callable[[str], None]], msg: str) -> None:
    """Call a progress callback safely when present."""
    try:
        if fn:
            fn(msg)
    except Exception:
        pass
