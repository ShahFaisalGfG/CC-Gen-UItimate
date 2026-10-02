# folder_scanner.py - finds supported media files under folders without blocking the GUI thread
#
# Large folders (thousands of files, deep trees) used to freeze the window: the scan, a stat
# per file, and one model insert per file all ran on the GUI thread. This worker walks the tree
# with os.scandir, whose directory entries already carry file type and size on Windows, and
# hands rows to the model in batches sized by time, so the list fills smoothly and the UI keeps
# repainting. A scan can be cancelled at any time (new scan, clear list, app shutdown).

import logging
import os
import threading
import time
from typing import Callable, Iterable, Iterator, Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

_log = logging.getLogger(__name__)

# Rows are flushed to the GUI at most this often, or sooner once this many are waiting.
_FLUSH_INTERVAL_S = 0.1
_MAX_BATCH = 2000


def iter_files(
    roots: Iterable[str],
    extensions: frozenset[str],
    is_cancelled: Callable[[], bool] = lambda: False,
    on_error: Optional[Callable[[str], None]] = None,
) -> Iterator[tuple[str, int]]:
    """Yield (path, size_bytes) for every file under `roots` whose extension is in `extensions`.

    Directories are walked depth-first in case-insensitive name order, so results arrive in the
    order a file browser would list them. Symlinked directories are not followed (avoids loops),
    and unreadable directories are reported through `on_error` and skipped.
    """
    stack = list(reversed([os.path.normpath(r) for r in roots]))
    while stack:
        if is_cancelled():
            return
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                listing = sorted(entries, key=lambda e: e.name.casefold())
        except OSError as error:
            if on_error:
                on_error(f"Skipped {folder}: {error.strerror or error}")
            continue
        subfolders: list[str] = []
        for entry in listing:
            if is_cancelled():
                return
            try:
                if entry.is_dir(follow_symlinks=False):
                    subfolders.append(entry.path)
                elif os.path.splitext(entry.name)[1].lower() in extensions and entry.is_file():
                    yield entry.path, entry.stat().st_size
            except OSError as error:
                _log.debug("Skipping unreadable entry %s: %r", entry.path, error)
        stack.extend(reversed(subfolders))


class FolderScanSignals(QObject):
    """Signals a FolderScanWorker emits from its pool thread."""

    batchFound = Signal(list)       # list[tuple[str, int]] of (path, size)
    progress = Signal(int)          # files found so far
    error = Signal(str)
    finished = Signal(int, bool)    # (files found, cancelled)


class FolderScanWorker(QRunnable):
    """Walks one or more folders on a pool thread and reports matching files in batches."""

    def __init__(self, roots: list[str], extensions: frozenset[str]) -> None:
        super().__init__()
        self.setAutoDelete(False)  # the controller owns the worker so it can cancel it
        self._roots = roots
        self._extensions = extensions
        self._cancel = threading.Event()
        self.signals = FolderScanSignals()

    def cancel(self) -> None:
        """Stop the scan at the next directory entry; already-sent batches stay delivered."""
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        """True once cancel() has been called."""
        return self._cancel.is_set()

    @Slot()
    def run(self) -> None:
        """Scan the roots, flushing batches on a time budget, then report completion."""
        found = 0
        batch: list[tuple[str, int]] = []
        last_flush = time.monotonic()
        try:
            for item in iter_files(self._roots, self._extensions, self._cancel.is_set, self.signals.error.emit):
                batch.append(item)
                found += 1
                now = time.monotonic()
                if len(batch) >= _MAX_BATCH or now - last_flush >= _FLUSH_INTERVAL_S:
                    self._flush(batch, found)
                    batch, last_flush = [], now
        except Exception as error:
            _log.error("Folder scan failed: %r", error, exc_info=True)
            self.signals.error.emit(f"Folder scan stopped: {error}")
        finally:
            try:
                if batch and not self._cancel.is_set():
                    self._flush(batch, found)
                self.signals.finished.emit(found, self._cancel.is_set())
            except RuntimeError:
                pass  # the app is shutting down and the signal object is already gone

    def _flush(self, batch: list[tuple[str, int]], found: int) -> None:
        """Send one batch of rows and the running total to the GUI thread."""
        if self._cancel.is_set():
            return
        self.signals.batchFound.emit(batch)
        self.signals.progress.emit(found)
