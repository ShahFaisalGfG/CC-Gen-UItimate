# test_pipeline.py - unit tests for ccgen.core.pipeline

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




    def test_skips_translator_preload_when_source_equals_target(self, mock_env):
        pipeline = Pipeline(_make_config(translate=True, source_lang="en", target_lang="en"))
        pipeline.prepare()
        mock_env["translator"].ensure_model.assert_not_called()


def _fake_translate(units, progress_cb=None, progress_num_cb=None, segment_cb=None):
    """Stand-in for translate_segments that prefixes each unit and streams it like the engine."""
    results = []
    for unit in units:
        translated = {
            "id": unit["id"], "start": unit["start"], "end": unit["end"],
            "original": unit["text"], "translated": "ES " + unit["text"], "language": "es",
        }
        if segment_cb:
            segment_cb(translated)
        results.append(translated)
    return results


def _streaming_transcribe(segments):
    """Stand-in for transcribe that streams each segment through segment_cb like WhisperEngine."""

    def fake(audio_path, language=None, beam_size=5, vad_filter=True,
             progress_cb=None, segment_cb=None, progress_num_cb=None):
        for seg in segments:
            if segment_cb:
                segment_cb(seg)
        return segments

    return fake


def _media_run(tmp_path, mock_env, segments, **config):
    """Run the pipeline on a fake media file whose transcription returns `segments`."""
    mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
    mock_env["transcriber"].transcribe.return_value = segments
    return Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"), **config))


class TestRunHappyPath:
    def test_returns_success_result_with_cues(self, tmp_path, mock_env, sample_segments):
        result = _media_run(tmp_path, mock_env, sample_segments).run()

        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert [cue["text"] for cue in result.segments] == [
            "Hello world, this is a test.",
            "The quick brown fox jumps over the lazy dog.",
        ]
        assert [cue["id"] for cue in result.segments] == [0, 1]
        assert result.detected_language == "en"
        assert result.error == ""

    def test_cue_timing_comes_from_word_timestamps(self, tmp_path, mock_env, sample_segments):
        result = _media_run(tmp_path, mock_env, sample_segments).run()
        first = result.segments[0]
        assert (first["start"], first["end"]) == (0.0, 2.2)

    def test_long_segment_is_split_into_readable_cues(self, tmp_path, mock_env):
        words = [
            {"word": f" word{i:02d}" + ("." if i == 9 else ""), "start": i * 0.4, "end": i * 0.4 + 0.35}
            for i in range(30)
        ]
        segment = {
            "id": 0, "start": 0.0, "end": 12.0, "language": "en",
            "text": "".join(w["word"] for w in words), "words": words,
        }
        result = _media_run(tmp_path, mock_env, [segment]).run()

        assert len(result.segments) > 1
        assert all(len(cue["text"]) <= 84 for cue in result.segments)
        assert result.segments[0]["text"].endswith("word09.")
        rejoined = " ".join(cue["text"] for cue in result.segments)
        assert rejoined == segment["text"].strip()

    def test_writes_srt_by_default(self, tmp_path, mock_env, sample_segments):
        result = _media_run(tmp_path, mock_env, sample_segments).run()

        expected = str(tmp_path / "movie.srt")
        assert result.output_files == [expected]
        assert os.path.exists(expected)

    def test_writes_both_formats_when_both_enabled(self, tmp_path, mock_env, sample_segments):
        result = _media_run(tmp_path, mock_env, sample_segments, emit_srt=True, emit_vtt=True).run()

        assert len(result.output_files) == 2
        assert all(os.path.exists(p) for p in result.output_files)

    def test_writes_all_five_formats_when_all_enabled(self, tmp_path, mock_env, sample_segments):
        result = _media_run(
            tmp_path, mock_env, sample_segments,
            emit_srt=True, emit_vtt=True, emit_lrc=True, emit_ass=True, emit_sbv=True,
        ).run()

        assert len(result.output_files) == 5
        assert all(os.path.exists(p) for p in result.output_files)
        exts = {os.path.splitext(p)[1] for p in result.output_files}
        assert exts == {".srt", ".vtt", ".lrc", ".ass", ".sbv"}

    def test_no_format_selected_fails_without_transcribing(self, tmp_path, mock_env, sample_segments):
        result = _media_run(tmp_path, mock_env, sample_segments, emit_srt=False).run()

        assert result.success is False
        assert "No output format selected" in result.error
        mock_env["extract_audio"].assert_not_called()

    def test_output_written_even_when_no_segments(self, tmp_path, mock_env):
        result = _media_run(tmp_path, mock_env, []).run()

        assert result.detected_language == ""
        assert result.output_files == [str(tmp_path / "movie.srt")]

    def test_cleanup_temp_called_with_audio_path(self, tmp_path, mock_env, sample_segments):
        _media_run(tmp_path, mock_env, sample_segments).run()

        mock_env["cleanup_temp"].assert_called_once_with(str(tmp_path / "audio.wav"))

    def test_transcribe_called_with_expected_arguments(self, tmp_path, mock_env, sample_segments):
        pipeline = _media_run(tmp_path, mock_env, sample_segments, language="en", beam_size=3, vad_filter=False)
        pipeline.run()

        args, kwargs = mock_env["transcriber"].transcribe.call_args
        assert args == (str(tmp_path / "audio.wav"),)
        assert (kwargs["language"], kwargs["beam_size"], kwargs["vad_filter"]) == ("en", 3, False)
        assert callable(kwargs["progress_cb"])
        assert callable(kwargs["segment_cb"])
        assert callable(kwargs["progress_num_cb"])

    def test_cues_stream_to_segment_cb_during_transcription(self, tmp_path, mock_env, sample_segments):
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.side_effect = _streaming_transcribe(sample_segments)
        received = []

        Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"))).run(segment_cb=received.append)

        assert [seg["text"] for seg in received] == [
            "Hello world, this is a test.",
            "The quick brown fox jumps over the lazy dog.",
        ]

    def test_status_messages_and_progress_forwarded(self, tmp_path, mock_env, sample_segments):
        def fake_transcribe(audio_path, **kwargs):
            kwargs["progress_num_cb"](500, 1000)
            return sample_segments

        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.side_effect = fake_transcribe
        messages, progress = [], []

        Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"))).run(
            messages.append, None, lambda done, total: progress.append((done, total)),
        )

        assert messages[:2] == ["Extracting audio...", "Transcribing..."]
        assert messages[-1] == "Done."
        assert progress == [(500, 1000)]


class TestCancellation:
    def test_cancel_during_transcription_returns_cancelled_result(self, tmp_path, mock_env, sample_segments):
        def fake_transcribe(audio_path, **kwargs):
            pipeline.cancel()
            kwargs["progress_num_cb"](1, 2)
            raise AssertionError("progress callback should have raised JobCancelled")

        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.side_effect = fake_transcribe
        pipeline = Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4")))

        result = pipeline.run()

        assert result.success is False
        assert result.cancelled is True
        assert result.error == "Cancelled by user."
        assert result.output_files == []
        assert not os.path.exists(tmp_path / "movie.srt")
        mock_env["cleanup_temp"].assert_called_once()

    def test_cancel_before_run_writes_nothing(self, tmp_path, mock_env, sample_segments):
        pipeline = _media_run(tmp_path, mock_env, sample_segments)
        pipeline.cancel()

        result = pipeline.run()

        assert result.cancelled is True
        mock_env["transcriber"].transcribe.assert_not_called()
        assert result.output_files == []


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
        result = _media_run(tmp_path, mock_env, sample_segments, translate=False).run()

        assert result.translated_segments == []
        mock_env["create_translation"].assert_not_called()

    def test_skipped_when_no_segments(self, tmp_path, mock_env):
        result = _media_run(tmp_path, mock_env, [], translate=True, source_lang="en", target_lang="es").run()

        assert result.translated_segments == []
        mock_env["translator"].translate_segments.assert_not_called()

    def test_skipped_when_source_already_in_target_language(self, tmp_path, mock_env, sample_segments):
        messages = []
        pipeline = _media_run(tmp_path, mock_env, sample_segments, translate=True, source_lang="auto", target_lang="en")

        result = pipeline.run(progress_cb=messages.append)

        assert result.success is True
        assert result.translated_segments == []
        mock_env["translator"].translate_segments.assert_not_called()
        assert any("Translation skipped" in m for m in messages)
        assert result.output_files == [str(tmp_path / "movie.srt")]

    def test_translates_sentence_units_and_maps_back_to_cues(self, tmp_path, mock_env, sample_segments):
        mock_env["translator"].translate_segments.side_effect = _fake_translate
        pipeline = _media_run(tmp_path, mock_env, sample_segments, translate=True, source_lang="en", target_lang="es")

        result = pipeline.run()

        mock_env["translator"].set_pair.assert_called_once_with("en", "es")
        units = mock_env["translator"].translate_segments.call_args.args[0]
        assert [u["text"] for u in units] == [
            "Hello world, this is a test.",
            "The quick brown fox jumps over the lazy dog.",
        ]
        assert [t["translated"] for t in result.translated_segments] == [
            "ES Hello world, this is a test.",
            "ES The quick brown fox jumps over the lazy dog.",
        ]
        assert [t["id"] for t in result.translated_segments] == [0, 1]
        assert result.translated_segments[0]["start"] == result.segments[0]["start"]

    def test_sentence_split_across_cues_is_translated_once(self, tmp_path, mock_env):
        segments = [
            {"id": 0, "start": 0.0, "end": 2.0, "text": " I went to the market", "words": [], "language": "en"},
            {"id": 1, "start": 2.1, "end": 4.0, "text": " with my friend yesterday.", "words": [], "language": "en"},
        ]
        mock_env["translator"].translate_segments.side_effect = _fake_translate
        pipeline = _media_run(tmp_path, mock_env, segments, translate=True, source_lang="en", target_lang="es")

        result = pipeline.run()

        units = mock_env["translator"].translate_segments.call_args.args[0]
        assert [u["text"] for u in units] == ["I went to the market with my friend yesterday."]
        assert [t["id"] for t in result.translated_segments] == [0, 1]
        rejoined = " ".join(t["translated"] for t in result.translated_segments)
        assert rejoined == "ES I went to the market with my friend yesterday."

    def test_resolves_auto_source_from_detected_language(self, tmp_path, mock_env, sample_segments):
        mock_env["translator"].translate_segments.side_effect = _fake_translate
        _media_run(tmp_path, mock_env, sample_segments, translate=True, source_lang="auto", target_lang="es").run()

        mock_env["translator"].set_pair.assert_called_once_with("en", "es")

    def test_engine_failure_yields_error_result(self, tmp_path, mock_env, sample_segments):
        mock_env["translator"].translate_segments.side_effect = RuntimeError("engine exploded")
        pipeline = _media_run(tmp_path, mock_env, sample_segments, translate=True, source_lang="en", target_lang="es")

        result = pipeline.run()

        assert result.success is False
        assert "Translation step failed" in result.error
        assert "engine exploded" in result.error
        mock_env["cleanup_temp"].assert_called_once()

    def test_translated_cues_stream_to_segment_cb(self, tmp_path, mock_env, sample_segments):
        mock_env["translator"].translate_segments.side_effect = _fake_translate
        received = []
        pipeline = _media_run(tmp_path, mock_env, sample_segments, translate=True, source_lang="en", target_lang="es")

        pipeline.run(segment_cb=received.append)

        translated = [seg for seg in received if "translated" in seg]
        assert [seg["id"] for seg in translated] == [0, 1]

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
        result = _media_run(tmp_path, mock_env, sample_segments, transliterate=False).run()

        assert result.transliterated_segments == []
        mock_env["create_translit"].assert_not_called()

    def test_uses_transcription_cues_by_default(self, tmp_path, mock_env, sample_segments):
        mock_env["transliterator"].transliterate_segments.return_value = []

        result = _media_run(tmp_path, mock_env, sample_segments, transliterate=True).run()

        source = mock_env["transliterator"].transliterate_segments.call_args.args[0]
        assert source == result.segments

    def test_uses_translated_cues_when_configured(self, tmp_path, mock_env, sample_segments):
        mock_env["translator"].translate_segments.side_effect = _fake_translate
        mock_env["transliterator"].transliterate_segments.return_value = []

        result = _media_run(
            tmp_path, mock_env, sample_segments,
            translate=True, source_lang="en", target_lang="es",
            transliterate=True, translit_input="translation",
        ).run()

        source = mock_env["transliterator"].transliterate_segments.call_args.args[0]
        assert source == result.translated_segments

    def test_falls_back_to_transcription_when_translation_empty(self, tmp_path, mock_env, sample_segments):
        mock_env["transliterator"].transliterate_segments.return_value = []

        result = _media_run(
            tmp_path, mock_env, sample_segments, transliterate=True, translit_input="translation",
        ).run()

        source = mock_env["transliterator"].transliterate_segments.call_args.args[0]
        assert source == result.segments

    def test_engine_failure_yields_error_result(self, tmp_path, mock_env, sample_segments):
        mock_env["transliterator"].transliterate_segments.side_effect = ValueError("bad script")

        result = _media_run(tmp_path, mock_env, sample_segments, transliterate=True).run()

        assert result.success is False
        assert "Transliteration step failed" in result.error

    def test_callbacks_forwarded_to_transliterate_segments(self, tmp_path, mock_env, sample_segments):
        mock_env["transliterator"].transliterate_segments.return_value = []

        _media_run(tmp_path, mock_env, sample_segments, transliterate=True).run()

        _, status_cb, progress_cb, segment_cb = mock_env["transliterator"].transliterate_segments.call_args.args
        assert callable(status_cb) and callable(progress_cb) and callable(segment_cb)

    def test_output_file_naming_includes_schemes(self, tmp_path, mock_env, sample_segments):
        mock_env["transliterator"].transliterate_segments.return_value = [
            {
                "id": 0, "start": 0.0, "end": 3.5,
                "original": "Hello world.", "transliterated": "Halo warld.",
                "source_scheme": "roman", "target_scheme": "ur",
            },
        ]

        result = _media_run(
            tmp_path, mock_env, sample_segments, transliterate=True,
            translit_source="roman", translit_target="ur", emit_srt=True, emit_vtt=False,
        ).run()

        expected = str(tmp_path / "movie_tr_roman_ur.srt")
        assert expected in result.output_files
        assert os.path.exists(expected)


class TestRunCombinedStages:
    def test_all_stages_produce_six_output_files(self, tmp_path, mock_env, sample_segments):
        mock_env["translator"].translate_segments.side_effect = _fake_translate
        mock_env["transliterator"].transliterate_segments.return_value = [
            {
                "id": 0, "start": 0.0, "end": 3.5,
                "original": "x", "transliterated": "y",
                "source_scheme": "roman", "target_scheme": "ur",
            },
        ]

        result = _media_run(
            tmp_path, mock_env, sample_segments,
            translate=True, source_lang="en", target_lang="es",
            transliterate=True, translit_source="roman", translit_target="ur",
            emit_srt=True, emit_vtt=True,
        ).run()

        assert len(result.output_files) == 6
        assert all(os.path.exists(p) for p in result.output_files)


class TestOutputDir:
    def test_relocates_output_to_output_dir(self, tmp_path, mock_env, sample_segments):
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        config = _make_config(input_path=str(tmp_path / "source" / "movie.mp4"), output_dir=str(out_dir))
        result = Pipeline(config).run()

        expected = str(out_dir / "movie.srt")
        assert result.output_files == [expected]
        assert os.path.exists(expected)

    def test_creates_missing_output_dir(self, tmp_path, mock_env, sample_segments):
        out_dir = tmp_path / "new" / "subs"
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.return_value = sample_segments

        result = Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"), output_dir=str(out_dir))).run()

        assert result.success is True
        assert os.path.exists(out_dir / "movie.srt")

    def test_line_limits_applied_to_written_cues(self, tmp_path, mock_env, sample_segments):
        result = _media_run(tmp_path, mock_env, sample_segments, max_line_length=20, max_lines=2).run()

        content = open(result.output_files[0], encoding="utf-8").read()
        text_lines = [ln for ln in content.splitlines() if ln and "-->" not in ln and not ln.isdigit()]
        assert all(len(ln) <= 20 for ln in text_lines)


class TestRunErrorHandling:
    def test_transcriber_exception_yields_failure_result(self, tmp_path, mock_env):
        mock_env["extract_audio"].return_value = str(tmp_path / "audio.wav")
        mock_env["transcriber"].transcribe.side_effect = RuntimeError("model crashed")

        result = Pipeline(_make_config(input_path=str(tmp_path / "movie.mp4"))).run()

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
    def test_forwarded_to_translate_and_ensure_model(self, tmp_path, mock_env, sample_segments):
        def fake_translate(units, progress_cb, progress_num_cb, segment_cb):
            progress_num_cb(1, len(units))
            return _fake_translate(units)

        mock_env["translator"].translate_segments.side_effect = fake_translate
        progress = []
        pipeline = _media_run(tmp_path, mock_env, sample_segments, translate=True, source_lang="en", target_lang="es")

        pipeline.run(progress_num_cb=lambda done, total: progress.append((done, total)))

        assert progress == [(1, 2)]
        _, progress_arg = mock_env["translator"].ensure_model.call_args.args
        assert callable(progress_arg)
