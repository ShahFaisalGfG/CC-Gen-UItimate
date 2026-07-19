# download_progress.py — routes third-party model-download byte progress (Hugging Face Hub,
# faster-whisper, argostranslate) to a single per-thread callback so the UI can show a real
# download percentage instead of a generic "downloading..." spinner.

import importlib
import logging
import threading
import time
import urllib.request
from contextlib import contextmanager
from typing import Callable, Iterator, Optional, TypeVar

import argostranslate.networking as argos_networking
import faster_whisper.utils as fw_utils
from huggingface_hub import constants as hf_constants
from tqdm.auto import tqdm as base_tqdm

_log = logging.getLogger(__name__)


# Real download progress is only as granular as the byte chunks huggingface_hub's own
# http_get() reads at a time (each chunk read fires exactly one tqdm.update() call) - its
# 10 MB default means a single chunk can cover a large fraction of a small model in one
# jump, showing as "stuck" for a while then leaping close to 100%. Shrinking this while
# download_progress() is active makes every real transfer report much more often.
_HF_DOWNLOAD_CHUNK_SIZE = 1 * 1024 * 1024
# Throttled now that chunk shrinking guarantees plenty of real updates to sample from -
# unlike before, when huggingface_hub/faster-whisper reported through tqdm.update() only a
# handful of times per download and any throttle here silently dropped nearly all of them.
_REPORT_INTERVAL_S = 0.2
_CHUNK_SIZE = 65536
_HF_RETRY_COUNT = 3
_HF_RETRY_BACKOFF_S = 1.0

_T = TypeVar("_T")

_state = threading.local()


class DownloadCancelled(Exception):
    """Raised from a progress callback to unwind a download the user cancelled mid-transfer."""


# huggingface_hub._snapshot_download does `from .utils.tqdm import tqdm as hf_tqdm` at import
# time, then explicitly passes a caller's tqdm_class straight through for the aggregate
# byte-progress bar (snapshot_download() is what faster-whisper uses to fetch a Whisper
# model, and multi-file transformers repos also route through it) - so patching only the
# `huggingface_hub.utils.tqdm` submodule's own `tqdm` attribute below misses this module's
# already-bound `hf_tqdm` name entirely, silently leaving Whisper downloads with no progress
# and the UI stuck showing "queued" for the whole transfer.
_hf_snapshot_module = importlib.import_module("huggingface_hub._snapshot_download")

# huggingface_hub/utils/__init__.py re-exports the `tqdm` class under the same name as this
# submodule, shadowing it on the package object. `importlib` fetches the real module from
# sys.modules so patching its `tqdm` attribute reaches every hf_hub_download() call site.
_hf_tqdm_module = importlib.import_module("huggingface_hub.utils.tqdm")


class _ReportingTqdm(base_tqdm):
    """Silent tqdm bar that forwards throttled byte progress to the callback active at creation."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.pop("name", None)
        # snapshot_download also drives a second, file-count bar ("Fetching N files",
        # unit="it") through this same class alongside the real byte-progress bar
        # (unit="B") - only the latter is meaningful to report as download progress.
        self._is_bytes = kwargs.get("unit") == "B"
        kwargs["disable"] = True
        self._last_report = 0.0
        # Captured now, not re-read later from update()/close() - huggingface_hub's
        # snapshot_download fans per-file downloads out onto its own internal
        # ThreadPoolExecutor (thread_map), and those worker threads never inherit this
        # thread-local state, only bar construction happens on the thread that is actually
        # inside download_progress()'s `with` block.
        self._callback: Optional[Callable[[int, int], None]] = getattr(_state, "callback", None)
        self._cancel_check: Optional[Callable[[], bool]] = getattr(_state, "cancel_check", None)
        super().__init__(*args, **kwargs)

    def update(self, n: Optional[float] = 1) -> None:
        """Advance the counter, report (done, total), then raise if cancelled mid-transfer.

        Bypasses tqdm.update()'s own counting, since it no-ops entirely when disabled
        (its very first line is `if self.disable: return`, before touching `self.n`).
        """
        self.n += n or 0
        _report_bar(self)
        _maybe_cancel(self._cancel_check)

    def close(self) -> None:
        """Report final progress, then close the bar (a no-op on tqdm's side while disabled)."""
        _report_bar(self, force=True)
        super().close()


def _report_bar(bar: "_ReportingTqdm", force: bool = False) -> None:
    """Forward a tqdm bar's (n, total) to its captured callback, throttled by time."""
    if not bar._is_bytes:
        return
    now = time.monotonic()
    if not force and now - bar._last_report < _REPORT_INTERVAL_S:
        return
    bar._last_report = now
    if bar._callback is None:
        return
    try:
        bar._callback(int(bar.n), int(bar.total or 0))
    except Exception:
        _log.debug("Download progress callback raised", exc_info=True)


def _report_bytes(done: int, total: int) -> None:
    """Forward raw (done, total) bytes to the callback registered for the current thread."""
    callback: Optional[Callable[[int, int], None]] = getattr(_state, "callback", None)
    if callback is None:
        return
    try:
        callback(done, total)
    except Exception:
        _log.debug("Download progress callback raised", exc_info=True)


def _maybe_cancel(cancel_check: Optional[Callable[[], bool]]) -> None:
    """Raise DownloadCancelled when the caller's cancel flag has been set."""
    if cancel_check is not None and cancel_check():
        raise DownloadCancelled("Download cancelled")


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
                    _maybe_cancel(getattr(_state, "cancel_check", None))
                return b"".join(chunks)
        except DownloadCancelled:
            raise
        except Exception as e:
            attempts += 1
            _log.warning("Translation package download attempt failed: %r", e)
    return None


def retry_hf_load(load_fn: Callable[[], _T], attempts: int = _HF_RETRY_COUNT) -> _T:
    """Retry a Hugging Face Hub load a few times, since a cold download can race and fail once."""
    last_error: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return load_fn()
        except DownloadCancelled:
            raise
        except Exception as e:
            last_error = e
            _log.warning("Hugging Face model load attempt %d/%d failed: %r", attempt, attempts, e)
            if attempt < attempts:
                time.sleep(_HF_RETRY_BACKOFF_S * attempt)
    assert last_error is not None
    raise last_error


@contextmanager
def download_progress(callback: Optional[Callable[[int, int], None]]) -> Iterator[None]:
    """Route byte-level model-download progress to `callback` for the current thread.

    Patches faster-whisper's silent tqdm, Hugging Face Hub's default tqdm and download chunk
    size, and argostranslate's downloader so any nested model download reports real, smooth
    progress instead of staying silent or jumping in a few large steps.
    """
    if callback is None:
        yield
        return
    previous_callback = getattr(_state, "callback", None)
    original_fw_tqdm = fw_utils.disabled_tqdm
    original_hf_tqdm = _hf_tqdm_module.tqdm  # type: ignore[attr-defined]
    original_hf_snapshot_tqdm = getattr(_hf_snapshot_module, "hf_tqdm", None)
    original_argos_get = argos_networking.get
    original_hf_chunk_size = hf_constants.DOWNLOAD_CHUNK_SIZE
    _state.callback = callback
    fw_utils.disabled_tqdm = _ReportingTqdm
    _hf_tqdm_module.tqdm = _ReportingTqdm  # type: ignore[attr-defined]
    if original_hf_snapshot_tqdm is not None:
        _hf_snapshot_module.hf_tqdm = _ReportingTqdm  # type: ignore[attr-defined]
    argos_networking.get = _streaming_get
    hf_constants.DOWNLOAD_CHUNK_SIZE = _HF_DOWNLOAD_CHUNK_SIZE
    try:
        yield
    finally:
        _state.callback = previous_callback
        fw_utils.disabled_tqdm = original_fw_tqdm
        _hf_tqdm_module.tqdm = original_hf_tqdm  # type: ignore[attr-defined]
        if original_hf_snapshot_tqdm is not None:
            _hf_snapshot_module.hf_tqdm = original_hf_snapshot_tqdm  # type: ignore[attr-defined]
        argos_networking.get = original_argos_get
        hf_constants.DOWNLOAD_CHUNK_SIZE = original_hf_chunk_size


@contextmanager
def cancellable(cancel_check: Optional[Callable[[], bool]]) -> Iterator[None]:
    """Make `cancel_check` visible to every nested download_progress() call on this thread.

    Lets asset_registry's blocking download calls be interrupted at the next reported
    chunk (see _maybe_cancel) instead of only before they start.
    """
    if cancel_check is None:
        yield
        return
    previous = getattr(_state, "cancel_check", None)
    _state.cancel_check = cancel_check
    try:
        yield
    finally:
        _state.cancel_check = previous
