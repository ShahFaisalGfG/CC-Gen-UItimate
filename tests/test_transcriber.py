# test_transcriber.py — unit tests for ccgen.core.transcriber

from unittest.mock import MagicMock, patch

import pytest

from ccgen.core.transcriber import Transcriber


class TestTranscriber:
    def test_not_loaded_initially(self):
        t = Transcriber()
        assert not t.is_loaded()

    def test_load_sets_model(self):
        t = Transcriber()
        with patch("ccgen.core.transcriber.WhisperModel") as mock_cls:
            mock_cls.return_value = MagicMock()
            t.load()
        assert t.is_loaded()

    def test_load_calls_progress_cb(self):
        messages = []
        t = Transcriber()
        with patch("ccgen.core.transcriber.WhisperModel"):
            t.load(progress_cb=messages.append)
        assert any("Loading model" in m for m in messages)
        assert any("ready" in m.lower() for m in messages)

    def test_transcribe_without_load_raises(self, tmp_wav):
        t = Transcriber()
        with pytest.raises(RuntimeError, match="load\\(\\)"):
            t.transcribe(tmp_wav)

    def test_transcribe_missing_file_raises(self):
        t = Transcriber()
        with patch("ccgen.core.transcriber.WhisperModel"):
            t.load()
        with pytest.raises(FileNotFoundError):
            t.transcribe("/nonexistent/audio.wav")

    def test_transcribe_returns_segments(self, tmp_wav):
        t = Transcriber()
        mock_word = MagicMock()
        mock_word.word = " Hello"
        mock_word.start = 0.0
        mock_word.end = 0.5

        mock_seg = MagicMock()
        mock_seg.start = 0.0
        mock_seg.end = 2.0
        mock_seg.text = " Hello world"
        mock_seg.words = [mock_word]

        mock_info = MagicMock()
        mock_info.language = "en"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], mock_info)

        with patch("ccgen.core.transcriber.WhisperModel", return_value=mock_model):
            t.load()
            result = t.transcribe(tmp_wav)

        assert len(result) == 1
        assert result[0]["language"] == "en"
        assert result[0]["text"] == " Hello world"
        assert len(result[0]["words"]) == 1

    def test_unload_clears_model(self):
        t = Transcriber()
        with patch("ccgen.core.transcriber.WhisperModel"):
            t.load()
        assert t.is_loaded()
        t.unload()
        assert not t.is_loaded()
