# test_audio.py — unit tests for ccgen.core.audio

import os
from unittest.mock import MagicMock, patch

import pytest

from ccgen.core.audio import cleanup_temp, extract_audio


class TestExtractAudio:
    def test_missing_input_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_audio(str(tmp_path / "nonexistent.mp4"))

    def test_ffmpeg_missing_raises(self, tmp_path):
        fake = tmp_path / "video.mp4"
        fake.write_bytes(b"fake")
        with patch("ccgen.core.audio.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                extract_audio(str(fake))

    def test_ffmpeg_error_raises(self, tmp_path):
        fake = tmp_path / "video.mp4"
        fake.write_bytes(b"fake")
        with patch("ccgen.core.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("ccgen.core.audio._run_ffmpeg", side_effect=RuntimeError("ffmpeg error: bad file")):
                with pytest.raises(RuntimeError, match="ffmpeg error"):
                    extract_audio(str(fake))

    def test_returns_output_path(self, tmp_path):
        fake = tmp_path / "video.mp4"
        fake.write_bytes(b"fake")
        out = tmp_path / "output.wav"
        with patch("ccgen.core.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("ccgen.core.audio._run_ffmpeg"):
                result = extract_audio(str(fake), output_path=str(out))
        assert result == str(out)

    def test_creates_temp_when_no_output(self, tmp_path):
        fake = tmp_path / "video.mp4"
        fake.write_bytes(b"fake")
        with patch("ccgen.core.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("ccgen.core.audio._run_ffmpeg"):
                result = extract_audio(str(fake))
        assert result.endswith(".wav")
        cleanup_temp(result)


class TestCleanupTemp:
    def test_removes_existing_file(self, tmp_path):
        f = tmp_path / "temp.wav"
        f.write_bytes(b"data")
        cleanup_temp(str(f))
        assert not f.exists()

    def test_missing_file_does_not_raise(self):
        cleanup_temp("/nonexistent/path/temp.wav")
