# test_helpers.py — unit tests for ccgen.utils.helpers

import os
import sys
from typing import Any

import ccgen.utils.helpers as helpers_module
from ccgen.utils.helpers import (
    ensure_dir,
    format_bytes,
    format_duration_ms,
    format_seconds,
    resource_path,
    safe_stem,
)


class TestResourcePath:
    def test_dev_mode_returns_project_root_join(self):
        project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(helpers_module.__file__))
        ))
        result = resource_path("assets/icon.png")
        expected = os.path.normpath(os.path.join(project_root, "assets/icon.png"))
        assert result == expected

    def test_pyinstaller_mode_uses_meipass(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        result = resource_path("assets/icon.png")
        expected = os.path.normpath(os.path.join(str(tmp_path), "assets/icon.png"))
        assert result == expected

    def test_relative_input_stays_relative_join(self):
        result = resource_path("data.json")
        assert result.endswith("data.json")

    def test_invalid_relative_falls_back_to_input(self):
        bad_relative: Any = None
        assert resource_path(bad_relative) is None


class TestFormatSeconds:
    def test_under_a_minute(self):
        assert format_seconds(45) == "45s"

    def test_zero_seconds(self):
        assert format_seconds(0) == "0s"

    def test_exact_minute(self):
        assert format_seconds(60) == "1m 0s"

    def test_minutes_and_seconds(self):
        assert format_seconds(125) == "2m 5s"

    def test_hours_minutes_seconds(self):
        assert format_seconds(3725) == "1h 2m 5s"

    def test_truncates_fractional_seconds(self):
        assert format_seconds(59.9) == "59s"

    def test_negative_input_falls_back(self):
        bad_seconds: Any = "not-a-number"
        assert format_seconds(bad_seconds) == "0s"


class TestEnsureDir:
    def test_creates_missing_directory(self, tmp_path):
        target = tmp_path / "nested" / "dir"
        result = ensure_dir(str(target))
        assert result == str(target)
        assert os.path.isdir(target)

    def test_existing_directory_is_noop(self, tmp_path):
        result = ensure_dir(str(tmp_path))
        assert result == str(tmp_path)
        assert os.path.isdir(tmp_path)

    def test_invalid_path_does_not_raise(self):
        bad_path = "\0invalid"
        result = ensure_dir(bad_path)
        assert result == bad_path


class TestSafeStem:
    def test_strips_extension(self):
        assert safe_stem("/videos/movie.mp4") == "movie"

    def test_no_extension(self):
        assert safe_stem("/videos/movie") == "movie"

    def test_multiple_dots_keeps_last_stripped(self):
        assert safe_stem("archive.tar.gz") == "archive.tar"

    def test_windows_style_path(self):
        assert safe_stem("C:\\videos\\clip.mov") == "clip"


class TestFormatBytes:
    def test_bytes_under_1kb(self):
        assert format_bytes(500) == "500.0 B"

    def test_kilobytes(self):
        assert format_bytes(2048) == "2.0 KB"

    def test_megabytes(self):
        result = format_bytes(45 * 1024 * 1024)
        assert result == "45.0 MB"

    def test_gigabytes(self):
        result = format_bytes(2.5 * 1024 ** 3)
        assert result == "2.5 GB"

    def test_terabytes(self):
        result = format_bytes(3 * 1024 ** 4)
        assert result == "3.0 TB"

    def test_zero_bytes(self):
        assert format_bytes(0) == "0.0 B"

    def test_invalid_input_falls_back(self):
        bad_bytes: Any = "bad"
        assert format_bytes(bad_bytes) == "0 B"


class TestFormatDurationMs:
    def test_zero(self):
        assert format_duration_ms(0) == "00:00:00"

    def test_seconds_only(self):
        assert format_duration_ms(45) == "00:00:45"

    def test_minutes_and_seconds(self):
        assert format_duration_ms(125) == "00:02:05"

    def test_hours_minutes_seconds(self):
        assert format_duration_ms(3725) == "01:02:05"

    def test_truncates_fractional_seconds(self):
        assert format_duration_ms(59.9) == "00:00:59"

    def test_invalid_input_falls_back(self):
        bad_seconds: Any = "bad"
        assert format_duration_ms(bad_seconds) == "00:00:00"
