# test_file_model.py — unit tests for ccgen.models.file_model.MediaFileModel

import pytest
from PySide6.QtCore import QCoreApplication

from ccgen.models.file_model import MediaFileModel


@pytest.fixture(scope="session")
def qt_app():
    """Provide a single QCoreApplication instance for headless Qt object tests."""
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


@pytest.fixture
def two_files(tmp_path):
    """Create two small real files on disk and return their paths."""
    first = tmp_path / "clip_one.mp4"
    second = tmp_path / "clip_two.wav"
    first.write_bytes(b"a" * 1024)
    second.write_bytes(b"b" * 2048)
    return [str(first), str(second)]


@pytest.fixture
def model(qt_app):
    return MediaFileModel()


class TestAddFiles:
    def test_adds_files_and_updates_count(self, model, two_files):
        model.addFiles(two_files)
        assert model.count == 2
        assert model.rowCount() == 2

    def test_role_data_matches_file_metadata(self, model, two_files):
        model.addFiles(two_files)
        index = model.index(0)
        assert model.data(index, MediaFileModel.NameRole) == "clip_one.mp4"
        assert model.data(index, MediaFileModel.PathRole) == two_files[0]
        assert model.data(index, MediaFileModel.ExtRole) == "MP4"
        assert model.data(index, MediaFileModel.StatusRole) == "pending"
        assert model.data(index, MediaFileModel.SelectedRole) is False

    def test_size_role_is_formatted_string(self, model, two_files):
        model.addFiles(two_files)
        index = model.index(0)
        assert model.data(index, MediaFileModel.SizeRole) == "1.0 KB"

    def test_total_size_reflects_all_files(self, model, two_files):
        model.addFiles(two_files)
        assert model.totalSize == "3.0 KB"

    def test_missing_file_is_skipped(self, model, tmp_path):
        missing = str(tmp_path / "does_not_exist.mp4")
        model.addFiles([missing])
        assert model.count == 0

    def test_duplicate_path_is_not_added_twice(self, model, two_files):
        model.addFiles([two_files[0]])
        model.addFiles([two_files[0]])
        assert model.count == 1

    def test_invalid_index_returns_none(self, model, two_files):
        model.addFiles(two_files)
        out_of_range = model.index(5)
        assert model.data(out_of_range, MediaFileModel.NameRole) is None


class TestRemoveAt:
    def test_removes_item_and_updates_count(self, model, two_files):
        model.addFiles(two_files)
        model.removeAt(0)
        assert model.count == 1
        assert model.getPaths() == [two_files[1]]

    def test_out_of_range_row_is_noop(self, model, two_files):
        model.addFiles(two_files)
        model.removeAt(99)
        assert model.count == 2

    def test_removing_shifts_selection_indices(self, model, two_files):
        model.addFiles(two_files)
        model.toggleSelection(1)
        model.removeAt(0)
        assert model.selectedCount == 1
        index = model.index(0)
        assert model.data(index, MediaFileModel.SelectedRole) is True


class TestRemoveSelected:
    def test_removes_only_selected_rows(self, model, two_files):
        model.addFiles(two_files)
        model.toggleSelection(0)
        model.removeSelected()
        assert model.count == 1
        assert model.getPaths() == [two_files[1]]
        assert model.selectedCount == 0

    def test_no_selection_removes_nothing(self, model, two_files):
        model.addFiles(two_files)
        model.removeSelected()
        assert model.count == 2


class TestSelectAll:
    def test_selects_every_row(self, model, two_files):
        model.addFiles(two_files)
        model.selectAll()
        assert model.selectedCount == 2

    def test_empty_model_selects_nothing(self, model):
        model.selectAll()
        assert model.selectedCount == 0


class TestClearSelection:
    def test_clears_all_selected_rows(self, model, two_files):
        model.addFiles(two_files)
        model.selectAll()
        model.clearSelection()
        assert model.selectedCount == 0


class TestToggleSelection:
    def test_toggle_on_then_off(self, model, two_files):
        model.addFiles(two_files)
        model.toggleSelection(0)
        assert model.selectedCount == 1
        model.toggleSelection(0)
        assert model.selectedCount == 0


class TestGetPaths:
    def test_returns_paths_in_insertion_order(self, model, two_files):
        model.addFiles(two_files)
        assert model.getPaths() == two_files

    def test_empty_model_returns_empty_list(self, model):
        assert model.getPaths() == []


class TestClearAll:
    def test_removes_all_files_and_resets_selection(self, model, two_files):
        model.addFiles(two_files)
        model.selectAll()
        model.clearAll()
        assert model.count == 0
        assert model.selectedCount == 0
        assert model.totalSize == "0.0 B"


class TestSetStatus:
    def test_updates_status_for_row(self, model, two_files):
        model.addFiles(two_files)
        model.setStatus(0, "done")
        index = model.index(0)
        assert model.data(index, MediaFileModel.StatusRole) == "done"
