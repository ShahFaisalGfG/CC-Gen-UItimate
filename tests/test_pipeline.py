# test_pipeline.py — unit tests for ccgen.core.pipeline

import os
from unittest.mock import MagicMock, patch

import pytest

from ccgen.core.pipeline import Pipeline, PipelineConfig, PipelineResult


def _make_config(**overrides) -> PipelineConfig:
    """Build a minimal PipelineConfig for tests, applying any overrides."""
    overrides.setdefault("input_path", "/videos/movie.mp4")
    return PipelineConfig(**overrides)


@pytest.fixture
def mock_env():
    """Patch engine factories and audio helpers so no real model or ffmpeg ever runs."""
    with (
        patch("ccgen.core.pipeline.create_caption_engine") as create_caption,
        patch("ccgen.core.pipeline.create_translation_engine") as create_translation,
        patch("ccgen.core.pipeline.create_transliteration_engine") as create_translit,
        patch("ccgen.core.pipeline.extract_audio") as extract_audio,
        patch("ccgen.core.pipeline.cleanup_temp") as cleanup_temp,
    ):
        transcriber = MagicMock(name="transcriber")
        translator = MagicMock(name="translator")
        transliterator = MagicMock(name="transliterator")
        create_caption.return_value = transcriber
        create_translation.return_value = translator
        create_translit.return_value = transliterator
        yield {
            "create_caption": create_caption,
            "create_translation": create_translation,
            "create_translit": create_translit,
            "extract_audio": extract_audio,
            "cleanup_temp": cleanup_temp,
            "transcriber": transcriber,
            "translator": translator,
            "transliterator": transliterator,
        }


class TestPipelineInit:
    def test_creates_transcriber_for_media_input(self, mock_env):
        config = _make_config(input_path="/videos/movie.mp4", model_name="small", device="cpu", compute_type="int8")
        Pipeline(config)
        mock_env["create_caption"].assert_called_once_with(model_name="small", device="cpu", compute_type="int8")

    def test_skips_transcriber_for_subtitle_input(self, mock_env):
        config = _make_config(input_path="/videos/movie.srt")
        Pipeline(config)
        mock_env["create_caption"].assert_not_called()

    def test_creates_translator_when_translate_enabled(self, mock_env):
        config = _make_config(translate=True, source_lang="en", target_lang="es")
        Pipeline(config)
        mock_env["create_translation"].assert_called_once_with(source_lang="en", target_lang="es")

    def test_skips_translator_when_translate_disabled(self, mock_env):
        config = _make_config(translate=False)
        Pipeline(config)
        mock_env["create_translation"].assert_not_called()

    def test_creates_transliterator_when_enabled(self, mock_env):
        config = _make_config(transliterate=True, translit_engine="rule", translit_source="roman", translit_target="ur")
        Pipeline(config)
        mock_env["create_translit"].assert_called_once_with("rule", source_scheme="roman", target_scheme="ur")

    def test_skips_transliterator_when_disabled(self, mock_env):
        config = _make_config(transliterate=False)
        Pipeline(config)
        mock_env["create_translit"].assert_not_called()


class TestPrepare:
    def test_loads_transcriber_with_no_callbacks(self, mock_env):
        pipeline = Pipeline(_make_config(input_path="/videos/movie.mp4"))
        pipeline.prepare()
        mock_env["transcriber"].load.assert_called_once_with(None, None)

    def test_forwards_callbacks_to_transcriber_load(self, mock_env):
        pipeline = Pipeline(_make_config(input_path="/videos/movie.mp4"))
        progress_cb, progress_num_cb = MagicMock(), MagicMock()
        pipeline.prepare(progress_cb, progress_num_cb)
        mock_env["transcriber"].load.assert_called_once_with(progress_cb, progress_num_cb)

    def test_skips_transcriber_load_for_subtitle_input(self, mock_env):
        pipeline = Pipeline(_make_config(input_path="/videos/movie.srt"))
        pipeline.prepare()
        mock_env["transcriber"].load.assert_not_called()

    def test_preloads_translator_when_source_lang_explicit(self, mock_env):
        config = _make_config(translate=True, source_lang="en", target_lang="es")
        pipeline = Pipeline(config)
        pipeline.prepare()
        mock_env["translator"].ensure_model.assert_called_once_with(None, None)

    def test_skips_translator_preload_when_source_lang_auto(self, mock_env):
        config = _make_config(translate=True, source_lang="auto", target_lang="es")
        pipeline = Pipeline(config)
        pipeline.prepare()
        mock_env["translator"].ensure_model.assert_not_called()

    def test_skips_translator_preload_when_translate_disabled(self, mock_env):
        pipeline = Pipeline(_make_config(translate=False))
        pipeline.prepare()
        mock_env["translator"].ensure_model.assert_not_called()

    def test_forwards_progress_num_cb_to_translator_preload(self, mock_env):
        config = _make_config(translate=True, source_lang="en", target_lang="es")
        pipeline = Pipeline(config)
        progress_num_cb = MagicMock()
        pipeline.prepare(progress_num_cb=progress_num_cb)
        mock_env["translator"].ensure_model.assert_called_once_with(None, progress_num_cb)

    def test_propagates_runtime_error_from_transcriber_load(self, mock_env):
        pipeline = Pipeline(_make_config(input_path="/videos/movie.mp4"))
        mock_env["transcriber"].load.side_effect = RuntimeError("model download failed")
        with pytest.raises(RuntimeError, match="model download failed"):
            pipeline.prepare()


class TestRunHappyPath:
    def test_returns_success_result(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        result = Pipeline(_make_config(input_path=input_path)).run()

        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert result.segments == sample_segments
        assert result.detected_language == "en"
        assert result.error == ""

    def test_writes_srt_by_default(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        result = Pipeline(_make_config(input_path=input_path)).run()

        expected = str(tmp_path / "movie.srt")
        assert result.output_files == [expected]
        assert os.path.exists(expected)

    def test_writes_both_formats_when_both_enabled(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        config = _make_config(input_path=input_path, emit_srt=True, emit_vtt=True)
        result = Pipeline(config).run()

        assert len(result.output_files) == 2
        assert all(os.path.exists(p) for p in result.output_files)

    def test_writes_all_five_formats_when_all_enabled(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        config = _make_config(
            input_path=input_path,
            emit_srt=True, emit_vtt=True, emit_lrc=True, emit_ass=True, emit_sbv=True,
        )
        result = Pipeline(config).run()

        assert len(result.output_files) == 5
        assert all(os.path.exists(p) for p in result.output_files)
        exts = {os.path.splitext(p)[1] for p in result.output_files}
        assert exts == {".srt", ".vtt", ".lrc", ".ass", ".sbv"}

    def test_output_written_even_when_no_segments(self, tmp_path, mock_env):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = []

        result = Pipeline(_make_config(input_path=input_path)).run()

        assert result.detected_language == ""
        assert result.output_files == [str(tmp_path / "movie.srt")]

    def test_cleanup_temp_called_with_audio_path(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        audio_path = str(tmp_path / "audio.wav")
        mock_env["extract_audio"].return_value = audio_path
        mock_env["transcriber"].transcribe.return_value = sample_segments

        Pipeline(_make_config(input_path=input_path)).run()

        mock_env["cleanup_temp"].assert_called_once_with(audio_path)

    def test_transcribe_called_with_expected_arguments(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        audio_path = str(tmp_path / "audio.wav")
        mock_env["extract_audio"].return_value = audio_path
        mock_env["transcriber"].transcribe.return_value = sample_segments

        config = _make_config(input_path=input_path, language="en", beam_size=3, vad_filter=False)
        progress_cb, segment_cb, progress_num_cb = MagicMock(), MagicMock(), MagicMock()
        Pipeline(config).run(progress_cb, segment_cb, progress_num_cb)

        mock_env["transcriber"].transcribe.assert_called_once_with(
            audio_path,
            language="en",
            beam_size=3,
            vad_filter=False,
            progress_cb=progress_cb,
            segment_cb=segment_cb,
            progress_num_cb=progress_num_cb,
        )


class TestRunSubtitleInput:
    def test_skips_transcriber_and_uses_parse_subtitle(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.srt")
        pipeline = Pipeline(_make_config(input_path=input_path))
        with patch("ccgen.core.pipeline.parse_subtitle", return_value=sample_segments) as parse_mock:
            result = pipeline.run()

        parse_mock.assert_called_once_with(input_path)
        mock_env["extract_audio"].assert_not_called()
        assert result.success is True
        assert result.segments == sample_segments

    def test_cleanup_temp_not_called_for_subtitle_input(self, tmp_path, mock_env, sample_segments):
        pipeline = Pipeline(_make_config(input_path=str(tmp_path / "movie.vtt")))
        with patch("ccgen.core.pipeline.parse_subtitle", return_value=sample_segments):
            pipeline.run()
        mock_env["cleanup_temp"].assert_not_called()

    def test_segment_cb_invoked_for_each_segment(self, tmp_path, mock_env, sample_segments):
        pipeline = Pipeline(_make_config(input_path=str(tmp_path / "movie.srt")))
        segment_cb = MagicMock()
        with patch("ccgen.core.pipeline.parse_subtitle", return_value=sample_segments):
            pipeline.run(segment_cb=segment_cb)
        assert segment_cb.call_count == len(sample_segments)

    def test_no_plain_subtitle_written_when_input_is_subtitle(self, tmp_path, mock_env, sample_segments):
        pipeline = Pipeline(_make_config(input_path=str(tmp_path / "movie.srt")))
        with patch("ccgen.core.pipeline.parse_subtitle", return_value=sample_segments):
            result = pipeline.run()
        assert result.output_files == []

    def test_detected_language_uses_config_language(self, tmp_path, mock_env, sample_segments):
        config = _make_config(input_path=str(tmp_path / "movie.srt"), language="fr")
        pipeline = Pipeline(config)
        with patch("ccgen.core.pipeline.parse_subtitle", return_value=sample_segments):
            result = pipeline.run()
        assert result.detected_language == "fr"


class TestRunTranslation:
    def test_skipped_when_translate_disabled(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        result = Pipeline(_make_config(input_path=input_path, translate=False)).run()

        assert result.translated_segments == []
        mock_env["create_translation"].assert_not_called()

    def test_skipped_when_no_segments(self, tmp_path, mock_env):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = []

        config = _make_config(input_path=input_path, translate=True, source_lang="en", target_lang="es")
        result = Pipeline(config).run()

        assert result.translated_segments == []
        mock_env["translator"].translate_segments.assert_not_called()

    def test_happy_path_calls_engine_in_order(self, tmp_path, mock_env, sample_segments, sample_translated_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["translator"].translate_segments.return_value = sample_translated_segments

        config = _make_config(input_path=input_path, translate=True, source_lang="en", target_lang="es")
        result = Pipeline(config).run()

        mock_env["translator"].set_pair.assert_called_once_with("en", "es")
        mock_env["translator"].ensure_model.assert_called_once_with(None, None)
        mock_env["translator"].translate_segments.assert_called_once_with(sample_segments, None, None, None)
        assert result.translated_segments == sample_translated_segments

    def test_resolves_auto_source_from_detected_language(self, tmp_path, mock_env, sample_segments, sample_translated_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["translator"].translate_segments.return_value = sample_translated_segments

        config = _make_config(input_path=input_path, translate=True, source_lang="auto", target_lang="es")
        Pipeline(config).run()

        mock_env["translator"].set_pair.assert_called_once_with("en", "es")

    def test_engine_failure_yields_error_result(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["translator"].translate_segments.side_effect = RuntimeError("engine exploded")

        config = _make_config(input_path=input_path, translate=True, source_lang="en", target_lang="es")
        result = Pipeline(config).run()

        assert result.success is False
        assert "Translation step failed" in result.error
        assert "engine exploded" in result.error
        mock_env["cleanup_temp"].assert_called_once()

    def test_segment_cb_forwarded_to_translate_segments(
        self, tmp_path, mock_env, sample_segments, sample_translated_segments
    ):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["translator"].translate_segments.return_value = sample_translated_segments
        segment_cb = MagicMock()

        config = _make_config(input_path=input_path, translate=True, source_lang="en", target_lang="es")
        Pipeline(config).run(segment_cb=segment_cb)

        mock_env["translator"].translate_segments.assert_called_once_with(
            sample_segments, None, None, segment_cb
        )

    def test_missing_source_lang_for_subtitle_input_fails(self, tmp_path, mock_env, sample_segments):
        config = _make_config(
            input_path=str(tmp_path / "movie.srt"), translate=True, source_lang="auto", target_lang="es"
        )
        pipeline = Pipeline(config)
        with patch("ccgen.core.pipeline.parse_subtitle", return_value=sample_segments):
            result = pipeline.run()

        assert result.success is False
        assert "Source language is required" in result.error


class TestRunTransliteration:
    def test_skipped_when_disabled(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        result = Pipeline(_make_config(input_path=input_path, transliterate=False)).run()

        assert result.transliterated_segments == []
        mock_env["create_translit"].assert_not_called()

    def test_uses_transcription_segments_by_default(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["transliterator"].transliterate_segments.return_value = []

        Pipeline(_make_config(input_path=input_path, transliterate=True)).run()

        mock_env["transliterator"].transliterate_segments.assert_called_once_with(
            sample_segments, None, None, None
        )

    def test_uses_translated_segments_when_configured(self, tmp_path, mock_env, sample_segments, sample_translated_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["translator"].translate_segments.return_value = sample_translated_segments
        mock_env["transliterator"].transliterate_segments.return_value = []

        config = _make_config(
            input_path=input_path,
            translate=True, source_lang="en", target_lang="es",
            transliterate=True, translit_input="translation",
        )
        Pipeline(config).run()

        mock_env["transliterator"].transliterate_segments.assert_called_once_with(
            sample_translated_segments, None, None, None
        )

    def test_falls_back_to_transcription_when_translation_empty(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["transliterator"].transliterate_segments.return_value = []

        config = _make_config(input_path=input_path, transliterate=True, translit_input="translation")
        Pipeline(config).run()

        mock_env["transliterator"].transliterate_segments.assert_called_once_with(
            sample_segments, None, None, None
        )

    def test_engine_failure_yields_error_result(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["transliterator"].transliterate_segments.side_effect = ValueError("bad script")

        result = Pipeline(_make_config(input_path=input_path, transliterate=True)).run()

        assert result.success is False
        assert "Transliteration step failed" in result.error

    def test_segment_cb_forwarded_to_transliterate_segments(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["transliterator"].transliterate_segments.return_value = []
        segment_cb = MagicMock()

        config = _make_config(input_path=input_path, transliterate=True)
        Pipeline(config).run(segment_cb=segment_cb)

        mock_env["transliterator"].transliterate_segments.assert_called_once_with(
            sample_segments, None, None, segment_cb
        )

    def test_output_file_naming_includes_schemes(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        translit_result = [
            {
                "id": 0, "start": 0.0, "end": 3.5,
                "original": "Hello world.", "transliterated": "Halo warld.",
                "source_scheme": "roman", "target_scheme": "ur",
            },
        ]
        mock_env["transliterator"].transliterate_segments.return_value = translit_result

        config = _make_config(
            input_path=input_path, transliterate=True,
            translit_source="roman", translit_target="ur",
            emit_srt=True, emit_vtt=False,
        )
        result = Pipeline(config).run()

        expected = str(tmp_path / "movie_tr_roman_ur.srt")
        assert expected in result.output_files
        assert os.path.exists(expected)


class TestRunCombinedStages:
    def test_all_stages_produce_six_output_files(
        self, tmp_path, mock_env, sample_segments, sample_translated_segments
    ):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["translator"].translate_segments.return_value = sample_translated_segments
        mock_env["transliterator"].transliterate_segments.return_value = [
            {
                "id": 0, "start": 0.0, "end": 3.5,
                "original": "x", "transliterated": "y",
                "source_scheme": "roman", "target_scheme": "ur",
            },
        ]

        config = _make_config(
            input_path=input_path,
            translate=True, source_lang="en", target_lang="es",
            transliterate=True, translit_source="roman", translit_target="ur",
            emit_srt=True, emit_vtt=True,
        )
        result = Pipeline(config).run()

        assert len(result.output_files) == 6
        assert all(os.path.exists(p) for p in result.output_files)


class TestOutputDir:
    def test_relocates_output_to_output_dir(self, tmp_path, mock_env, sample_segments):
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        input_path = str(tmp_path / "source" / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        config = _make_config(input_path=input_path, output_dir=str(out_dir))
        result = Pipeline(config).run()

        expected = str(out_dir / "movie.srt")
        assert result.output_files == [expected]
        assert os.path.exists(expected)


class TestRunErrorHandling:
    def test_transcriber_exception_yields_failure_result(self, tmp_path, mock_env):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.side_effect = RuntimeError("model crashed")

        result = Pipeline(_make_config(input_path=input_path)).run()

        assert isinstance(result, PipelineResult)
        assert result.success is False
        assert "model crashed" in result.error
        assert result.output_files == []

    def test_extract_audio_exception_yields_failure_result(self, tmp_path, mock_env):
        mock_env["extract_audio"].side_effect = RuntimeError("ffmpeg missing")

        result = Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"))).run()

        assert result.success is False
        assert "ffmpeg missing" in result.error

    def test_cleanup_temp_called_even_on_transcribe_failure(self, tmp_path, mock_env):
        audio_path = str(tmp_path / "audio.wav")
        mock_env["extract_audio"].return_value = audio_path
        mock_env["transcriber"].transcribe.side_effect = RuntimeError("model crashed")

        Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"))).run()

        mock_env["cleanup_temp"].assert_called_once_with(audio_path)

    def test_cleanup_temp_not_called_when_audio_never_extracted(self, tmp_path, mock_env):
        mock_env["extract_audio"].side_effect = RuntimeError("ffmpeg missing")

        Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"))).run()

        mock_env["cleanup_temp"].assert_not_called()

    def test_run_never_raises(self, tmp_path, mock_env):
        mock_env["extract_audio"].side_effect = ValueError("weird failure")
        try:
            result = Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"))).run()
        except Exception as exc:
            pytest.fail(f"run() raised unexpectedly: {exc!r}")
        assert result.success is False


class TestProgressNumCbForwarding:
    def test_forwarded_to_transcribe(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        progress_num_cb = MagicMock()

        Pipeline(_make_config(input_path=input_path)).run(progress_num_cb=progress_num_cb)

        _, kwargs = mock_env["transcriber"].transcribe.call_args
        assert kwargs["progress_num_cb"] is progress_num_cb

    def test_forwarded_to_translate_and_ensure_model(
        self, tmp_path, mock_env, sample_segments, sample_translated_segments
    ):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["translator"].translate_segments.return_value = sample_translated_segments
        progress_num_cb = MagicMock()

        config = _make_config(input_path=input_path, translate=True, source_lang="en", target_lang="es")
        Pipeline(config).run(progress_num_cb=progress_num_cb)

        mock_env["translator"].ensure_model.assert_called_once_with(None, progress_num_cb)
        mock_env["translator"].translate_segments.assert_called_once_with(
            sample_segments, None, progress_num_cb, None
        )

    def test_forwarded_to_transliterate(self, tmp_path, mock_env, sample_segments):
        input_path = str(tmp_path / "movie.mp4")
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments
        mock_env["transliterator"].transliterate_segments.return_value = []
        progress_num_cb = MagicMock()

        config = _make_config(input_path=input_path, transliterate=True)
        Pipeline(config).run(progress_num_cb=progress_num_cb)

        mock_env["transliterator"].transliterate_segments.assert_called_once_with(
            sample_segments, None, progress_num_cb, None
        )
