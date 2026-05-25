# test_pipeline.py — unit tests for ccgen.core.pipeline

import os
from unittest.mock import MagicMock, patch

import pytest

from ccgen.core.pipeline import Pipeline, PipelineConfig


def _make_config(tmp_path, **kwargs) -> PipelineConfig:
    fake = tmp_path / "video.mp4"
    fake.write_bytes(b"fake")
    return PipelineConfig(input_path=str(fake), **kwargs)


class TestPipeline:
    def test_prepare_raises_on_model_failure(self, tmp_path):
        config = _make_config(tmp_path)
        pipeline = Pipeline(config)
        with patch.object(pipeline._transcriber, "load", side_effect=RuntimeError("load failed")):
            with pytest.raises(RuntimeError, match="load failed"):
                pipeline.prepare()

    def test_run_returns_failure_on_audio_error(self, tmp_path):
        config = _make_config(tmp_path)
        pipeline = Pipeline(config)
        with patch.object(pipeline._transcriber, "load"):
            pipeline.prepare()
        with patch("ccgen.core.pipeline.extract_audio", side_effect=RuntimeError("ffmpeg error")):
            result = pipeline.run()
        assert not result.success
        assert "ffmpeg error" in result.error

    def test_run_returns_success_with_srt(self, tmp_path, sample_segments):
        config = _make_config(tmp_path, emit_srt=True, emit_vtt=False)
        pipeline = Pipeline(config)

        with patch.object(pipeline._transcriber, "load"):
            pipeline.prepare()
        with patch("ccgen.core.pipeline.extract_audio", return_value="/tmp/audio.wav"):
            with patch("ccgen.core.pipeline.cleanup_temp"):
                with patch.object(
                    pipeline._transcriber, "transcribe", return_value=sample_segments
                ):
                    with patch("ccgen.core.pipeline.write_srt") as mock_srt:
                        mock_srt.return_value = str(tmp_path / "video.srt")
                        result = pipeline.run()

        assert result.success
        assert len(result.segments) == 2
        assert result.detected_language == "en"

    def test_run_no_translation_when_disabled(self, tmp_path, sample_segments):
        config = _make_config(tmp_path, translate=False)
        pipeline = Pipeline(config)
        assert pipeline._translator is None

    def test_run_cleans_temp_on_failure(self, tmp_path):
        config = _make_config(tmp_path)
        pipeline = Pipeline(config)
        with patch.object(pipeline._transcriber, "load"):
            pipeline.prepare()

        cleaned = []
        with patch("ccgen.core.pipeline.extract_audio", return_value="/tmp/x.wav"):
            with patch("ccgen.core.pipeline.cleanup_temp", side_effect=lambda p: cleaned.append(p)):
                with patch.object(
                    pipeline._transcriber, "transcribe", side_effect=RuntimeError("crash")
                ):
                    result = pipeline.run()

        assert not result.success
        assert "/tmp/x.wav" in cleaned
