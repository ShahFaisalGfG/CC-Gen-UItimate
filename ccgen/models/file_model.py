# file_model.py — QAbstractListModel backing the QML file queue

import os

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


class MediaFileModel(QAbstractListModel):
    """List model that exposes media file metadata and processing status to QML."""

    NameRole     = _UserRole + 1
    PathRole     = _UserRole + 2
    SizeRole     = _UserRole + 3
    ExtRole      = _UserRole + 4
    SelectedRole = _UserRole + 5
    StatusRole   = _UserRole + 6

    countChanged      = Signal(int)
    totalSizeChanged  = Signal()
    selectionChanged  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[dict] = []
        self._selected: set[int] = set()
        self._total_bytes: int = 0

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
            case self.SelectedRole: return index.row() in self._selected
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
        }

    # ── Mutation API ─────────────────────────────────────────────────────────

    @Slot(list)
    def addFiles(self, paths: list) -> None:
        """Add multiple files by path, skipping duplicates and missing files."""
        for path in paths:
            try:
                self._add_one(str(path))
            except Exception:
                pass

    @Slot(int)
    def removeAt(self, row: int) -> None:
        """Remove the item at the given row index."""
        try:
            if 0 <= row < len(self._files):
                self.beginRemoveRows(QModelIndex(), row, row)
                removed = self._files.pop(row)
                self._total_bytes -= removed["bytes"]
                self._selected = {i if i < row else i - 1 for i in self._selected if i != row}
                self.endRemoveRows()
                self.countChanged.emit(len(self._files))
                self.totalSizeChanged.emit()
                self.selectionChanged.emit()
        except Exception:
            pass

    @Slot()
    def removeSelected(self) -> None:
        """Remove all currently selected items."""
        try:
            for row in sorted(self._selected, reverse=True):
                if 0 <= row < len(self._files):
                    self.beginRemoveRows(QModelIndex(), row, row)
                    removed = self._files.pop(row)
                    self._total_bytes -= removed["bytes"]
                    self.endRemoveRows()
            self._selected.clear()
            self.countChanged.emit(len(self._files))
            self.totalSizeChanged.emit()
            self.selectionChanged.emit()
        except Exception:
            pass

    @Slot()
    def clearAll(self) -> None:
        """Remove all items from the model."""
        try:
            self.beginResetModel()
            self._files.clear()
            self._selected.clear()
            self._total_bytes = 0
            self.endResetModel()
            self.countChanged.emit(0)
            self.totalSizeChanged.emit()
            self.selectionChanged.emit()
        except Exception:
            pass

    @Slot(int)
    def toggleSelection(self, row: int) -> None:
        """Toggle the selected state of a single item."""
        try:
            if 0 <= row < len(self._files):
                if row in self._selected:
                    self._selected.discard(row)
                else:
                    self._selected.add(row)
                idx = self.index(row)
                self.dataChanged.emit(idx, idx, [self.SelectedRole])
                self.selectionChanged.emit()
        except Exception:
            pass

    @Slot()
    def selectAll(self) -> None:
        """Select all items."""
        try:
            self._selected = set(range(len(self._files)))
            if self._files:
                self.dataChanged.emit(
                    self.index(0), self.index(len(self._files) - 1), [self.SelectedRole]
                )
            self.selectionChanged.emit()
        except Exception:
            pass

    @Slot()
    def clearSelection(self) -> None:
        """Deselect all items."""
        try:
            if self._selected:
                self._selected.clear()
                if self._files:
                    self.dataChanged.emit(
                        self.index(0), self.index(len(self._files) - 1), [self.SelectedRole]
                    )
            self.selectionChanged.emit()
        except Exception:
            pass

    @Slot(int)
    def setSingle(self, row: int) -> None:
        """Deselect all, then select only the given row."""
        try:
            if 0 <= row < len(self._files):
                old = self._selected.copy()
                self._selected = {row}
                changed = old.symmetric_difference(self._selected)
                if changed:
                    indices = sorted(changed)
                    self.dataChanged.emit(
                        self.index(indices[0]), self.index(indices[-1]), [self.SelectedRole]
                    )
                self.selectionChanged.emit()
        except Exception:
            pass

    @Slot(int, int)
    def selectRange(self, anchor: int, target: int) -> None:
        """Replace selection with all rows between anchor and target (inclusive)."""
        try:
            lo = max(0, min(anchor, target))
            hi = min(len(self._files) - 1, max(anchor, target))
            old = self._selected.copy()
            self._selected = set(range(lo, hi + 1))
            changed = old.symmetric_difference(self._selected)
            if changed:
                indices = sorted(changed)
                self.dataChanged.emit(
                    self.index(indices[0]), self.index(indices[-1]), [self.SelectedRole]
                )
            self.selectionChanged.emit()
        except Exception:
            pass

    @Slot(int, str)
    def setStatus(self, row: int, status: str) -> None:
        """Update the processing status of a single item."""
        try:
            if 0 <= row < len(self._files):
                self._files[row]["status"] = status
                idx = self.index(row)
                self.dataChanged.emit(idx, idx, [self.StatusRole])
        except Exception:
            pass

    # ── Query API ────────────────────────────────────────────────────────────

    @Property(int, notify=countChanged)
    def count(self) -> int:
        """Total number of files in the queue."""
        return len(self._files)

    @Property(str, notify=totalSizeChanged)
    def totalSize(self) -> str:
        """Formatted combined size of all files."""
        try:
            return format_bytes(float(self._total_bytes))
        except Exception:
            return "0 B"

    @Property(int, notify=selectionChanged)
    def selectedCount(self) -> int:
        """Number of currently selected items."""
        return len(self._selected)

    @Slot(result=list)
    def getPaths(self) -> list:
        """Return a list of all file paths in the model."""
        return [f["path"] for f in self._files]

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _add_one(self, path: str) -> None:
        """Add a single file if it exists and is not already in the queue."""
        path = os.path.normpath(path)
        if any(f["path"] == path for f in self._files):
            return
        if not os.path.isfile(path):
            return
        item = self._make_item(path)
        self.beginInsertRows(QModelIndex(), len(self._files), len(self._files))
        self._files.append(item)
        self._total_bytes += item["bytes"]
        self.endInsertRows()
        self.countChanged.emit(len(self._files))
        self.totalSizeChanged.emit()

    @staticmethod
    def _make_item(path: str) -> dict:
        """Build a file metadata dict for a given path."""
        try:
            size_bytes = os.path.getsize(path)
            size_str = format_bytes(float(size_bytes))
        except Exception:
            size_bytes = 0
            size_str = "?"
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lstrip(".").upper() or "FILE"
        return {
            "name": name,
            "path": path,
            "size": size_str,
            "bytes": size_bytes,
            "ext": ext,
            "status": "pending",
        }
