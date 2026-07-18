# download_progress.py — routes third-party model-download byte progress (Hugging Face Hub,
# faster-whisper, argostranslate) to a single per-thread callback so the UI can show a real
# download percentage instead of a generic "downloading..." spinner.

import importlib
import logging
import threading
import time
import urllib.request
from contextlib import contextmanager
from typing import Callable, Iterator, Optional

import argostranslate.networking as argos_networking
import faster_whisper.utils as fw_utils
from tqdm.auto import tqdm as base_tqdm

_log = logging.getLogger(__name__)

_REPORT_INTERVAL_S = 0.15
_CHUNK_SIZE = 65536

_state = threading.local()

# huggingface_hub/utils/__init__.py re-exports the `tqdm` class under the same name as this
# submodule, shadowing it on the package object. `importlib` fetches the real module from
# sys.modules so patching its `tqdm` attribute reaches every hf_hub_download() call site.
_hf_tqdm_module = importlib.import_module("huggingface_hub.utils.tqdm")


class _ReportingTqdm(base_tqdm):
    """Silent tqdm bar that forwards throttled byte progress to the active thread's callback."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.pop("name", None)
        kwargs["disable"] = True
        self._last_report = 0.0
        super().__init__(*args, **kwargs)

    def update(self, n: Optional[float] = 1) -> None:
        """Advance the counter and report the new (done, total) to the active callback.

        Bypasses tqdm.update()'s own counting, since it no-ops entirely when disabled
        (its very first line is `if self.disable: return`, before touching `self.n`).
        """
        self.n += n or 0
        _report_bar(self)

    def close(self) -> None:
        """Report final progress, then close the bar (a no-op on tqdm's side while disabled)."""
        _report_bar(self, force=True)
        super().close()


def _report_bar(bar: "_ReportingTqdm", force: bool = False) -> None:
    """Forward a tqdm bar's (n, total) to the current thread's callback, throttled by time."""
    now = time.monotonic()
    if not force and now - bar._last_report < _REPORT_INTERVAL_S:
        return
    bar._last_report = now
    _report_bytes(int(bar.n), int(bar.total or 0))


def _report_bytes(done: int, total: int) -> None:
    """Forward raw (done, total) bytes to the callback registered for the current thread."""
    callback: Optional[Callable[[int, int], None]] = getattr(_state, "callback", None)
    if callback is None:
        return
    try:
        callback(done, total)
    except Exception:
        _log.debug("Download progress callback raised", exc_info=True)


def _streaming_get(url: str, retry_count: int = 3) -> Optional[bytes]:
    """Drop-in replacement for argostranslate's `networking.get` that reports chunk progress."""
    attempts = 0
    while attempts <= retry_count:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ArgosTranslate"})
            with urllib.request.urlopen(request) as response:
                total = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                chunks: list[bytes] = []
                while True:
                    chunk = response.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    _report_bytes(downloaded, total)
                return b"".join(chunks)
        except Exception as e:
            attempts += 1
            _log.warning("Translation package download attempt failed: %r", e)
    return None


@contextmanager
def download_progress(callback: Optional[Callable[[int, int], None]]) -> Iterator[None]:
    """Route byte-level model-download progress to `callback` for the current thread.

    Patches faster-whisper's silent tqdm, Hugging Face Hub's default tqdm, and argostranslate's
    downloader so any nested model download reports real progress instead of staying silent.
    """
    if callback is None:
        yield
        return
    previous_callback = getattr(_state, "callback", None)
    original_fw_tqdm = fw_utils.disabled_tqdm
    original_hf_tqdm = _hf_tqdm_module.tqdm  # type: ignore[attr-defined]
    original_argos_get = argos_networking.get
    _state.callback = callback
    fw_utils.disabled_tqdm = _ReportingTqdm
    _hf_tqdm_module.tqdm = _ReportingTqdm  # type: ignore[attr-defined]
    argos_networking.get = _streaming_get
    try:
        yield
    finally:
        _state.callback = previous_callback
        fw_utils.disabled_tqdm = original_fw_tqdm
        _hf_tqdm_module.tqdm = original_hf_tqdm  # type: ignore[attr-defined]
        argos_networking.get = original_argos_get
