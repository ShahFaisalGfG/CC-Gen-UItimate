# test_logging.py - unit tests for ccgen.utils.logging

import logging

import pytest

import ccgen.utils.logging as log_module


@pytest.fixture(autouse=True)
def isolated_logs(tmp_path, monkeypatch):
    """Point the log file at a temp folder and detach the handler after each test."""
    log_module.configure_logging(enabled=False)
    monkeypatch.setattr(log_module, "get_logs_dir", lambda: str(tmp_path))
    yield tmp_path
    log_module.configure_logging(enabled=False)


class TestConfigureLogging:
    def test_enabled_writes_warnings_to_file(self, isolated_logs):
        log_module.configure_logging(True, "critical")
        logging.getLogger("ccgen.test").warning("disk is full")
        logging.getLogger("ccgen.test").info("routine detail")
        content = (isolated_logs / "ccgen.log").read_text(encoding="utf-8")
        assert "disk is full" in content
        assert "routine detail" not in content

    def test_all_level_records_debug(self, isolated_logs):
        log_module.configure_logging(True, "all")
        logging.getLogger("ccgen.test").debug("fine detail")
        assert "fine detail" in (isolated_logs / "ccgen.log").read_text(encoding="utf-8")

    def test_disabled_detaches_file_handler(self, isolated_logs):
        log_module.configure_logging(True, "all")
        log_module.configure_logging(False, "all")
        logging.getLogger("ccgen.test").error("after disable")
        log_file = isolated_logs / "ccgen.log"
        assert not log_file.exists() or "after disable" not in log_file.read_text(encoding="utf-8")


class TestClearLogs:
    def test_truncates_active_log(self, isolated_logs):
        log_module.configure_logging(True, "all")
        logging.getLogger("ccgen.test").error("old entry")
        assert log_module.clear_logs() is True
        assert (isolated_logs / "ccgen.log").read_text(encoding="utf-8") == ""
