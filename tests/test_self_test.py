# test_self_test.py - unit tests for the build self-test runner (ccgen.utils.self_test)

import pytest

from ccgen.utils import self_test
from ccgen.utils.self_test import run_self_test


def _fail() -> None:
    raise ImportError("No module named 'missing_lib'")


class TestRunSelfTest:
    def test_all_passing_returns_zero_and_writes_report(self, tmp_path):
        report = tmp_path / "report.txt"

        code = run_self_test(str(report), checks=[("First", lambda: None), ("Second", lambda: None)])

        assert code == 0
        assert report.read_text(encoding="utf-8").splitlines() == [
            "PASS  First", "PASS  Second", "All 2 checks passed",
        ]

    def test_failure_returns_one_and_keeps_running_later_checks(self, tmp_path):
        report = tmp_path / "report.txt"
        ran = []

        code = run_self_test(str(report), checks=[("Broken", _fail), ("After", lambda: ran.append(True))])

        text = report.read_text(encoding="utf-8")
        assert code == 1
        assert "FAIL  Broken: ImportError(\"No module named 'missing_lib'\")" in text
        assert "PASS  After" in text
        assert text.rstrip().endswith("1 of 2 checks failed")
        assert ran == [True]

    def test_without_report_path_writes_only_stdout(self, capsys):
        assert run_self_test(None, checks=[("Only", lambda: None)]) == 0
        assert "PASS  Only" in capsys.readouterr().out


class TestQmlCheck:
    def _use_qml_dir(self, monkeypatch, folder) -> None:
        monkeypatch.setattr(self_test, "resource_path", lambda _relative: str(folder))

    def test_valid_qml_passes(self, tmp_path, monkeypatch):
        (tmp_path / "Ok.qml").write_text("import QtQuick\nItem {}\n", encoding="utf-8")
        self._use_qml_dir(monkeypatch, tmp_path)

        self_test._check_qml()

    def test_missing_qt_module_fails(self, tmp_path, monkeypatch):
        (tmp_path / "Broken.qml").write_text("import QtQuick.DoesNotExist\nItem {}\n", encoding="utf-8")
        self._use_qml_dir(monkeypatch, tmp_path)

        with pytest.raises(RuntimeError, match="QtQuick.DoesNotExist"):
            self_test._check_qml()

    def test_empty_qml_folder_fails(self, tmp_path, monkeypatch):
        self._use_qml_dir(monkeypatch, tmp_path)

        with pytest.raises(RuntimeError, match="no QML files"):
            self_test._check_qml()
