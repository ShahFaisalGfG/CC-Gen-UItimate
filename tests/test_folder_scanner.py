# test_folder_scanner.py - unit tests for ccgen.services.folder_scanner

import time

from PySide6.QtCore import QCoreApplication

from ccgen.models.file_model import SUPPORTED_EXTS
from ccgen.services.folder_scanner import FolderScanWorker, iter_files


def _touch(path, size=10):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


class TestIterFiles:
    def test_finds_supported_files_recursively_in_name_order(self, tmp_path):
        _touch(tmp_path / "b.mp4", 5)
        _touch(tmp_path / "A.srt", 7)
        _touch(tmp_path / "notes.txt")
        _touch(tmp_path / "sub" / "c.WAV", 3)

        found = list(iter_files([str(tmp_path)], SUPPORTED_EXTS))

        names = [p.replace(str(tmp_path), "").lstrip("\\/") for p, _ in found]
        assert names == ["A.srt", "b.mp4", "sub\\c.WAV"] or names == ["A.srt", "b.mp4", "sub/c.WAV"]
        assert [size for _, size in found] == [7, 5, 3]

    def test_cancel_stops_iteration(self, tmp_path):
        for i in range(20):
            _touch(tmp_path / f"{i:02d}.mp3")
        seen = []
        for path, _ in iter_files([str(tmp_path)], SUPPORTED_EXTS, is_cancelled=lambda: len(seen) >= 3):
            seen.append(path)
        assert len(seen) == 3

    def test_unreadable_root_reports_error(self, tmp_path):
        errors = []
        assert list(iter_files([str(tmp_path / "missing")], SUPPORTED_EXTS, on_error=errors.append)) == []
        assert errors and "missing" in errors[0]

    def test_thousands_of_files_scan_quickly(self, tmp_path):
        for i in range(3000):
            (tmp_path / f"clip{i:04d}.mp4").write_bytes(b"")
        start = time.perf_counter()
        found = list(iter_files([str(tmp_path)], SUPPORTED_EXTS))
        assert len(found) == 3000
        assert time.perf_counter() - start < 5.0


class TestFolderScanWorker:
    def test_run_emits_batches_and_finish(self, tmp_path):
        if QCoreApplication.instance() is None:
            QCoreApplication([])
        for i in range(5):
            _touch(tmp_path / f"{i}.mp4")
        worker = FolderScanWorker([str(tmp_path)], SUPPORTED_EXTS)
        batches, finished = [], []
        worker.signals.batchFound.connect(batches.append)
        worker.signals.finished.connect(lambda found, cancelled: finished.append((found, cancelled)))

        worker.run()

        assert sum(len(b) for b in batches) == 5
        assert finished == [(5, False)]

    def test_cancelled_worker_sends_no_rows(self, tmp_path):
        if QCoreApplication.instance() is None:
            QCoreApplication([])
        _touch(tmp_path / "a.mp4")
        worker = FolderScanWorker([str(tmp_path)], SUPPORTED_EXTS)
        batches, finished = [], []
        worker.signals.batchFound.connect(batches.append)
        worker.signals.finished.connect(lambda found, cancelled: finished.append(cancelled))
        worker.cancel()

        worker.run()

        assert batches == []
        assert finished == [True]
