# voice_files.py - where speech models live on disk, and fetching, checking, and removing them
#
# XTTS-v2 comes from the Hugging Face Hub and lives in the shared Hugging Face cache, like the
# Whisper models. Piper voices and Kokoro's model are kept per voice under the app's local data
# folder, so one voice can be removed without touching the others. Nothing here loads a model,
# so the Manage Models catalog can check and manage files without importing torch or ONNX.

import logging
import os
import shutil
from typing import Callable, Optional

from huggingface_hub import hf_hub_download

from ccgen.config.defaults import AppInfo, ModelRepos
from ccgen.config.voices import ENGINE_KOKORO, ENGINE_PIPER, ENGINE_XTTS, VoiceOption
from ccgen.utils.download_progress import download_file, download_progress, retry_hf_load

_log = logging.getLogger(__name__)

ProgressCb = Optional[Callable[[int, int], None]]


def voices_root() -> str:
    """Folder holding downloaded Piper voices and the Kokoro model."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, AppInfo.APP_NAME, "voices")


def voice_dir(voice: VoiceOption) -> str:
    """Folder holding one voice's files (Kokoro voices share the engine's model folder)."""
    if voice.engine == ENGINE_KOKORO:
        return os.path.join(voices_root(), ENGINE_KOKORO)
    return os.path.join(voices_root(), ENGINE_PIPER, voice.voice_id)


def piper_files(voice: VoiceOption) -> tuple[str, str]:
    """Repository paths of a Piper voice's ONNX model and its JSON config."""
    model = f"{voice.model_path}/{voice.voice_id}.onnx"
    return model, f"{model}.json"


def kokoro_paths() -> tuple[str, str]:
    """Local paths of Kokoro's ONNX model and voice bank."""
    directory = os.path.join(voices_root(), ENGINE_KOKORO)
    return tuple(os.path.join(directory, name) for name, _, _ in ModelRepos.KOKORO_FILES)  # type: ignore[return-value]


def engine_files_cached(engine: str, voice: Optional[VoiceOption] = None) -> bool:
    """True when every file the engine (and, for Piper, the given voice) needs is on disk."""
    if engine == ENGINE_XTTS:
        return _xtts_paths(local_only=True) is not None
    if engine == ENGINE_KOKORO:
        return all(
            os.path.isfile(path) and os.path.getsize(path) == size
            for path, (_, size, _) in zip(kokoro_paths(), ModelRepos.KOKORO_FILES)
        )
    if voice is None:
        return False
    directory = voice_dir(voice)
    return all(os.path.isfile(os.path.join(directory, name)) for name in piper_files(voice))


def ensure_xtts(progress_num_cb: ProgressCb = None) -> str:
    """Download the XTTS-v2 checkpoint when needed; return its folder."""
    paths = _xtts_paths(local_only=True)
    if paths is None:
        with download_progress(progress_num_cb):
            paths = _xtts_paths(local_only=False)
    assert paths is not None
    return os.path.dirname(paths[0])


def ensure_kokoro(progress_num_cb: ProgressCb = None) -> tuple[str, str]:
    """Download Kokoro's model and voice bank when needed; return (model path, voices path)."""
    paths = kokoro_paths()
    with download_progress(progress_num_cb):
        for path, (name, size, sha256) in zip(paths, ModelRepos.KOKORO_FILES):
            if not (os.path.isfile(path) and os.path.getsize(path) == size):
                download_file(f"{ModelRepos.KOKORO_RELEASE}/{name}", path, size, sha256)
    return paths


def ensure_piper(voice: VoiceOption, progress_num_cb: ProgressCb = None) -> tuple[str, str]:
    """Download a Piper voice when needed; return (model path, config path)."""
    directory = voice_dir(voice)
    if engine_files_cached(ENGINE_PIPER, voice):
        return tuple(os.path.join(directory, name) for name in piper_files(voice))  # type: ignore[return-value]
    with download_progress(progress_num_cb):
        paths = [
            retry_hf_load(lambda name=name: hf_hub_download(ModelRepos.PIPER_VOICES, name, local_dir=directory))
            for name in piper_files(voice)
        ]
    return paths[0], paths[1]


def remove_engine_files(engine: str, voice: Optional[VoiceOption] = None) -> None:
    """Delete a Kokoro model or a single Piper voice from the voices folder."""
    if engine == ENGINE_KOKORO:
        target = os.path.join(voices_root(), ENGINE_KOKORO)
    elif engine == ENGINE_PIPER and voice is not None:
        target = voice_dir(voice)
    else:
        raise ValueError(f"Cannot remove files for {engine}.")
    root = os.path.realpath(voices_root())
    target = os.path.realpath(target)
    if os.path.commonpath((root, target)) != root or target == root:
        raise ValueError("Refusing to delete outside the voices folder.")
    if os.path.isdir(target):
        shutil.rmtree(target)


def folder_size(path: str) -> int:
    """Total size in bytes of every file under `path` (0 when it doesn't exist)."""
    return sum(
        os.path.getsize(os.path.join(base, name))
        for base, _, names in os.walk(path)
        for name in names
    )


def _xtts_paths(local_only: bool) -> Optional[list[str]]:
    """Resolve every XTTS file in the Hugging Face cache, or None when one is missing locally."""
    def fetch(name: str) -> str:
        return hf_hub_download(
            ModelRepos.XTTS, name, revision=ModelRepos.XTTS_REVISION, local_files_only=local_only,
        )

    try:
        if local_only:
            return [fetch(name) for name in ModelRepos.XTTS_FILES]
        return [retry_hf_load(lambda name=name: fetch(name)) for name in ModelRepos.XTTS_FILES]
    except OSError:
        if local_only:
            return None
        raise
