# file_model.py - QAbstractListModel backing the QML file queue
#
# Built to stay responsive with thousands of rows: duplicate checks use a path-key set,
# additions arrive as one batched insert, bulk removals rebuild the list in a single pass,
# and selection lives on each row so removing rows never has to renumber a selection set.

import os
from typing import Any, Optional

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    Signal,
    Slot,
)

from ccgen.utils.helpers import format_bytes

_UserRole = Qt.ItemDataRole.UserRole

VIDEO_EXTS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".ts", ".m2ts"})
AUDIO_EXTS = frozenset({".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"})
SUBTITLE_EXTS = frozenset({".srt", ".vtt", ".lrc", ".ass", ".ssa", ".sbv"})
SUPPORTED_EXTS = VIDEO_EXTS | AUDIO_EXTS | SUBTITLE_EXTS

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_DONE = "done"
STATUS_ERROR = "error"
STATUS_CANCELLED = "cancelled"


class MediaFileModel(QAbstractListModel):
    """List model that exposes media file metadata and processing status to QML."""

    NameRole      = _UserRole + 1
    PathRole      = _UserRole + 2
    SizeRole      = _UserRole + 3
    ExtRole       = _UserRole + 4
    SelectedRole  = _UserRole + 5
    StatusRole    = _UserRole + 6
    KindRole      = _UserRole + 7
    ProgressRole  = _UserRole + 8
    MessageRole   = _UserRole + 9
    FolderRole    = _UserRole + 10
    OutputsRole   = _UserRole + 11

    countChanged      = Signal(int)
    totalSizeChanged  = Signal()
    selectionChanged  = Signal()
    statusCountsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[dict[str, Any]] = []
        self._keys: set[str] = set()
        self._total_bytes: int = 0
        self._selected_count = 0

    # ── QAbstractListModel interface ─────────────────────────────────────────

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._files)

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._files):
            return None
        item = self._files[index.row()]
        match role:
            case self.NameRole:     return item["name"]
            case self.PathRole:     return item["path"]
            case self.SizeRole:     return item["size"]
            case self.ExtRole:      return item["ext"]
            case self.StatusRole:   return item["status"]
            case self.SelectedRole: return item["selected"]
            case self.KindRole:     return item["kind"]
            case self.ProgressRole: return item["progress"]
            case self.MessageRole:  return item["message"]
            case self.FolderRole:   return item["folder"]
            case self.OutputsRole:  return item["outputs"]
        if role == Qt.ItemDataRole.DisplayRole:
            return item["name"]
        return None

    def roleNames(self) -> dict:
        return {
            self.NameRole:     b"name",
            self.PathRole:     b"path",
            self.SizeRole:     b"size",
            self.ExtRole:      b"ext",
            self.SelectedRole: b"selected",
            self.StatusRole:   b"status",
            self.KindRole:     b"kind",
            self.ProgressRole: b"progress",
            self.MessageRole:  b"message",
            self.FolderRole:   b"folder",
            self.OutputsRole:  b"outputs",
        }

    # ── Adding rows ──────────────────────────────────────────────────────────

    @Slot(list)
    def addFiles(self, paths: list) -> None:
        """Add files by path, skipping duplicates, missing files, and unreadable entries."""
        items = []
        seen: set[str] = set()
        for path in paths:
            norm = os.path.normpath(str(path))
            key = os.path.normcase(norm)
            if key in self._keys or key in seen or not os.path.isfile(norm):
                continue
            try:
                size = os.path.getsize(norm)
            except OSError:
                size = 0
            seen.add(key)
            items.append(self._make_item(norm, size))
        self._insert(items)

    def addScanned(self, entries: list) -> int:
        """Add (path, size) pairs from a folder scan in one insert. Returns how many were new."""
        items = []
        seen: set[str] = set()
        for path, size in entries:
            norm = os.path.normpath(path)
            key = os.path.normcase(norm)
            if key in self._keys or key in seen:
                continue
            seen.add(key)
            items.append(self._make_item(norm, int(size)))
        self._insert(items)
        return len(items)

    # ── Removing rows ────────────────────────────────────────────────────────

    @Slot(int)
    def removeAt(self, row: int) -> None:
        """Remove the item at the given row index (a file being processed is kept)."""
        if 0 <= row < len(self._files) and self._files[row]["status"] != STATUS_PROCESSING:
            self.beginRemoveRows(QModelIndex(), row, row)
            self._forget(self._files.pop(row))
            self.endRemoveRows()
            self._emit_all_changed()

    @Slot()
    def removeSelected(self) -> None:
        """Remove all selected items except one that is being processed."""
        self._remove_where(lambda item: item["selected"] and item["status"] != STATUS_PROCESSING)

    @Slot()
    def removeFinished(self) -> None:
        """Remove every file that finished successfully."""
        self._remove_where(lambda item: item["status"] == STATUS_DONE)

    @Slot()
    def clearAll(self) -> None:
        """Remove all items except one that is being processed."""
        self._remove_where(lambda item: item["status"] != STATUS_PROCESSING)

    # ── Selection ────────────────────────────────────────────────────────────

    @Slot(int)
    def toggleSelection(self, row: int) -> None:
        """Toggle the selected state of a single item."""
        if 0 <= row < len(self._files):
            self._set_selected(row, not self._files[row]["selected"])
            self.selectionChanged.emit()

    @Slot()
    def selectAll(self) -> None:
        """Select all items."""
        self._select_rows(set(range(len(self._files))))

    @Slot()
    def clearSelection(self) -> None:
        """Deselect all items."""
        self._select_rows(set())

    @Slot(int)
    def setSingle(self, row: int) -> None:
        """Deselect all, then select only the given row."""
        if 0 <= row < len(self._files):
            self._select_rows({row})

    @Slot(int, int)
    def selectRange(self, anchor: int, target: int) -> None:
        """Replace selection with all rows between anchor and target (inclusive)."""
        lo = max(0, min(anchor, target))
        hi = min(len(self._files) - 1, max(anchor, target))
        self._select_rows(set(range(lo, hi + 1)))

    # ── Run state ────────────────────────────────────────────────────────────

    @Slot(int, str)
    def setStatus(self, row: int, status: str) -> None:
        """Update the processing status of a single item."""
        if 0 <= row < len(self._files):
            self._update(row, status=status)

    def set_run_state(
        self,
        path: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        outputs: Optional[list[str]] = None,
    ) -> None:
        """Update one file's run state by path; unknown paths (removed rows) are ignored."""
        row = self._row_of(path)
        if row < 0:
            return
        fields: dict[str, Any] = {}
        if status is not None:
            fields["status"] = status
        if progress is not None:
            fields["progress"] = progress
        if message is not None:
            fields["message"] = message
        if outputs is not None:
            fields["outputs"] = outputs
        self._update(row, **fields)

    def runnable_paths(self) -> list[str]:
        """Paths a new run should process: unfinished files, or every file when all are done."""
        unfinished = [f["path"] for f in self._files if f["status"] != STATUS_DONE]
        return unfinished or [f["path"] for f in self._files]

    def reset_for_run(self, paths: list[str]) -> None:
        """Mark the given files pending with cleared progress and messages."""
        for path in paths:
            self.set_run_state(path, status=STATUS_PENDING, progress=0.0, message="", outputs=[])

    def contains(self, path: str) -> bool:
        """Return True while the file is still in the queue."""
        return self._row_of(path) >= 0

    # ── Query API ────────────────────────────────────────────────────────────

    @Property(int, notify=countChanged)
    def count(self) -> int:
        """Total number of files in the queue."""
        return len(self._files)

    @Property(str, notify=totalSizeChanged)
    def totalSize(self) -> str:
        """Formatted combined size of all files."""
        return format_bytes(float(self._total_bytes))

    @Property(int, notify=selectionChanged)
    def selectedCount(self) -> int:
        """Number of currently selected items."""
        return self._selected_count

    @Property(int, notify=statusCountsChanged)
    def doneCount(self) -> int:
        """Number of files that finished successfully."""
        return sum(1 for f in self._files if f["status"] == STATUS_DONE)

    @Property(int, notify=statusCountsChanged)
    def failedCount(self) -> int:
        """Number of files whose last run failed."""
        return sum(1 for f in self._files if f["status"] == STATUS_ERROR)

    @Property(int, notify=statusCountsChanged)
    def runnableCount(self) -> int:
        """How many files the next Start would process (see runnable_paths)."""
        return len(self.runnable_paths())

    @Slot(result=list)
    def getPaths(self) -> list:
        """Return a list of all file paths in the model."""
        return [f["path"] for f in self._files]

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _make_item(path: str, size_bytes: int) -> dict[str, Any]:
        """Build a file metadata dict for a given path."""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        kind = "video" if ext in VIDEO_EXTS else "subtitle" if ext in SUBTITLE_EXTS else "audio"
        return {
            "name": name,
            "path": path,
            "folder": os.path.dirname(path),
            "size": format_bytes(float(size_bytes)),
            "bytes": size_bytes,
            "ext": ext.lstrip(".").upper() or "FILE",
            "kind": kind,
            "status": STATUS_PENDING,
            "progress": 0.0,
            "message": "",
            "outputs": [],
            "selected": False,
        }

    def _insert(self, items: list[dict[str, Any]]) -> None:
        """Append prepared rows with a single model insert."""
        if not items:
            return
        first = len(self._files)
        self.beginInsertRows(QModelIndex(), first, first + len(items) - 1)
        self._files.extend(items)
        for item in items:
            self._keys.add(os.path.normcase(item["path"]))
            self._total_bytes += item["bytes"]
        self.endInsertRows()
        self.countChanged.emit(len(self._files))
        self.totalSizeChanged.emit()
        self.statusCountsChanged.emit()

    def _remove_where(self, predicate) -> None:
        """Drop every row matching predicate in one pass and one model reset."""
        keep = [item for item in self._files if not predicate(item)]
        if len(keep) == len(self._files):
            return
        self.beginResetModel()
        self._files = keep
        self._keys = {os.path.normcase(item["path"]) for item in keep}
        self._total_bytes = sum(item["bytes"] for item in keep)
        self._selected_count = sum(1 for item in keep if item["selected"])
        self.endResetModel()
        self._emit_all_changed()

    def _forget(self, item: dict[str, Any]) -> None:
        """Update bookkeeping for one removed row."""
        self._keys.discard(os.path.normcase(item["path"]))
        self._total_bytes -= item["bytes"]
        if item["selected"]:
            self._selected_count -= 1

    def _emit_all_changed(self) -> None:
        """Notify QML that counts, size, selection, and status totals may have changed."""
        self.countChanged.emit(len(self._files))
        self.totalSizeChanged.emit()
        self.selectionChanged.emit()
        self.statusCountsChanged.emit()

    def _set_selected(self, row: int, selected: bool) -> None:
        """Set one row's selection flag and notify its delegate."""
        item = self._files[row]
        if item["selected"] != selected:
            item["selected"] = selected
            self._selected_count += 1 if selected else -1
            idx = self.index(row)
            self.dataChanged.emit(idx, idx, [self.SelectedRole])

    def _select_rows(self, rows: set[int]) -> None:
        """Make exactly `rows` selected, emitting one change range for the affected span."""
        changed = [
            row for row, item in enumerate(self._files) if item["selected"] != (row in rows)
        ]
        for row in changed:
            self._files[row]["selected"] = row in rows
        self._selected_count = len(rows)
        if changed:
            self.dataChanged.emit(self.index(changed[0]), self.index(changed[-1]), [self.SelectedRole])
        self.selectionChanged.emit()

    def _update(self, row: int, **fields: Any) -> None:
        """Apply field changes to one row and notify exactly the roles that changed."""
        role_for = {
            "status": self.StatusRole, "progress": self.ProgressRole,
            "message": self.MessageRole, "outputs": self.OutputsRole,
        }
        item = self._files[row]
        roles = [role_for[k] for k, v in fields.items() if item.get(k) != v]
        if not roles:
            return
        item.update(fields)
        idx = self.index(row)
        self.dataChanged.emit(idx, idx, roles)
        if "status" in fields:
            self.statusCountsChanged.emit()

    def _row_of(self, path: str) -> int:
        """Return the row of a path, or -1 when it is no longer in the queue."""
        key = os.path.normcase(os.path.normpath(path))
        if key not in self._keys:
            return -1
        for row, item in enumerate(self._files):
            if os.path.normcase(item["path"]) == key:
                return row
        return -1
