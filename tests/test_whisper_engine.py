# test_whisper_engine.py — unit tests for ccgen.engines.captions.whisper_engine

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ccgen.engines.captions.whisper_engine import WhisperEngine


def _fake_word(word: str, start: float, end: float) -> SimpleNamespace:
    return SimpleNamespace(word=word, start=start, end=end)


def _fake_segment(start: float, end: float, text: str, words=None) -> SimpleNamespace:
    return SimpleNamespace(start=start, end=end, text=text, words=words or [])


def _fake_info(language: str = "en", duration: float = 10.0) -> SimpleNamespace:
    return SimpleNamespace(language=language, duration=duration)


def _loaded_engine(mock_model_cls, segments, info, **kwargs) -> WhisperEngine:
    engine = WhisperEngine(**kwargs)
    mock_model_cls.return_value.transcribe.return_value = (segments, info)
    engine.load()
    return engine


class TestLoad:
    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_wraps_model_load_in_download_progress(self, mock_model_cls, mock_download_progress):
        engine = WhisperEngine(model_name="tiny", device="cpu", compute_type="int8")
        cb = MagicMock()
        engine.load(progress_num_cb=cb)
        mock_download_progress.assert_called_once_with(cb)
        mock_model_cls.assert_called_once_with("tiny", device="cpu", compute_type="int8")
        assert engine.is_loaded()

    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_progress_cb_messages(self, mock_model_cls, mock_download_progress):
        engine = WhisperEngine(model_name="tiny")
        messages = []
        engine.load(progress_cb=messages.append)
        assert messages == ["Loading model 'tiny'...", "Model ready."]

    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel", side_effect=RuntimeError("boom"))
    def test_construction_error_wrapped(self, mock_model_cls, mock_download_progress):
        engine = WhisperEngine(model_name="tiny")
        with pytest.raises(RuntimeError, match="Model load failed"):
            engine.load()


class TestTranscribeBeforeLoad:
    def test_raises_runtime_error(self, tmp_wav):
        engine = WhisperEngine()
        with pytest.raises(RuntimeError, match="Call load"):
            engine.transcribe(tmp_wav)


class TestTranscribeMissingAudio:
    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_raises_file_not_found(self, mock_model_cls, mock_download_progress, tmp_path):
        engine = _loaded_engine(mock_model_cls, [], _fake_info())
        with pytest.raises(FileNotFoundError):
            engine.transcribe(str(tmp_path / "missing.wav"))


class TestTranscribe:
    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_returns_segments_with_expected_shape(self, mock_model_cls, mock_download_progress, tmp_wav):
        seg1 = _fake_segment(0.0, 1.5, "Hello", words=[_fake_word("Hello", 0.0, 1.5)])
        seg2 = _fake_segment(1.5, 3.0, "world", words=[])
        info = _fake_info(language="en", duration=3.0)
        engine = _loaded_engine(mock_model_cls, [seg1, seg2], info)

        result = engine.transcribe(tmp_wav)

        assert len(result) == 2
        assert result[0]["id"] == 0
        assert result[0]["text"] == "Hello"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 1.5
        assert result[0]["words"] == [{"word": "Hello", "start": 0.0, "end": 1.5}]
        assert result[0]["language"] == "en"
        assert result[1]["id"] == 1
        assert result[1]["words"] == []

    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_segment_cb_fires_once_per_segment(self, mock_model_cls, mock_download_progress, tmp_wav):
        seg1 = _fake_segment(0.0, 1.0, "a")
        seg2 = _fake_segment(1.0, 2.0, "b")
        info = _fake_info(duration=2.0)
        engine = _loaded_engine(mock_model_cls, [seg1, seg2], info)

        received = []
        engine.transcribe(tmp_wav, segment_cb=received.append)

        assert len(received) == 2
        assert received[0]["text"] == "a"
        assert received[1]["text"] == "b"

    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_progress_num_cb_reports_ms(self, mock_model_cls, mock_download_progress, tmp_wav):
        seg1 = _fake_segment(0.0, 1.5, "a")
        seg2 = _fake_segment(1.5, 4.25, "b")
        info = _fake_info(duration=5.0)
        engine = _loaded_engine(mock_model_cls, [seg1, seg2], info)

        calls = []
        engine.transcribe(tmp_wav, progress_num_cb=lambda done, total: calls.append((done, total)))

        assert calls == [(1500, 5000), (4250, 5000)]

    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_detected_language_used_when_language_none(self, mock_model_cls, mock_download_progress, tmp_wav):
        seg1 = _fake_segment(0.0, 1.0, "a")
        info = _fake_info(language="fr", duration=1.0)
        engine = _loaded_engine(mock_model_cls, [seg1], info)

        result = engine.transcribe(tmp_wav, language=None)

        assert result[0]["language"] == "fr"

    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_requested_language_overrides_detected(self, mock_model_cls, mock_download_progress, tmp_wav):
        seg1 = _fake_segment(0.0, 1.0, "a")
        info = _fake_info(language="fr", duration=1.0)
        engine = _loaded_engine(mock_model_cls, [seg1], info)

        result = engine.transcribe(tmp_wav, language="en")

        assert result[0]["language"] == "en"


class TestIsLoadedAndUnload:
    def test_is_loaded_false_before_load(self):
        engine = WhisperEngine()
        assert engine.is_loaded() is False

    @patch("ccgen.engines.captions.whisper_engine.download_progress")
    @patch("ccgen.engines.captions.whisper_engine.WhisperModel")
    def test_unload_clears_model(self, mock_model_cls, mock_download_progress):
        engine = _loaded_engine(mock_model_cls, [], _fake_info())
        assert engine.is_loaded() is True
        engine.unload()
        assert engine.is_loaded() is False
