# test_task_transliterate.py - unit tests for ccgen.core.tasks.transliterate

import pytest

from ccgen.core.tasks.configs import TransliterateConfig
from ccgen.core.tasks.transliterate import TransliterateTask

_SRT = "1\n00:00:00,000 --> 00:00:02,000\nnamaste\n"


def _subtitle(tmp_path, name="movie_ur.srt"):
    """Write a one-cue subtitle file and return its path."""
    path = tmp_path / name
    path.write_text(_SRT, encoding="utf-8")
    return str(path)


class TestConfig:
    def test_rejects_identical_scripts(self, tmp_path):
        with pytest.raises(ValueError, match="two different"):
            TransliterateConfig(input_path=str(tmp_path / "a.srt"), source_scheme="ur", target_scheme="ur")

    def test_rejects_pair_the_neural_engine_lacks(self, tmp_path):
        with pytest.raises(ValueError, match="can't convert"):
            TransliterateConfig(
                input_path=str(tmp_path / "a.srt"), source_scheme="ta", target_scheme="te", engine="neural",
            )

    def test_rejects_media_input(self, tmp_path):
        with pytest.raises(ValueError, match="needs a subtitle file"):
            TransliterateConfig(input_path=str(tmp_path / "a.mp4"))


class TestRun:
    def test_converts_with_rule_engine_and_names_output(self, tmp_path):
        cfg = TransliterateConfig(input_path=_subtitle(tmp_path), source_scheme="roman", target_scheme="ur")
        result = TransliterateTask(cfg).run()
        assert result.success, result.error
        assert result.output_files == [str(tmp_path / "movie_tr_roman_ur.srt")]
        # The spoken language stays Urdu; only the script changed.
        assert result.output_languages == {str(tmp_path / "movie_tr_roman_ur.srt"): "ur"}
        assert "namaste" not in (tmp_path / "movie_tr_roman_ur.srt").read_text(encoding="utf-8")

    def test_streams_converted_cues(self, tmp_path):
        segments = []
        cfg = TransliterateConfig(input_path=_subtitle(tmp_path), source_scheme="roman", target_scheme="hi")
        TransliterateTask(cfg).run(segment_cb=segments.append)
        assert "transliterated" in segments[-1]

    def test_text_in_another_script_is_reported(self, tmp_path):
        path = tmp_path / "movie_ur.srt"
        path.write_text("1\n00:00:00,000 --> 00:00:02,000\nسلام.\n", encoding="utf-8")
        cfg = TransliterateConfig(input_path=str(path), source_scheme="roman", target_scheme="ur")
        result = TransliterateTask(cfg).run()
        assert result.success, result.error
        assert result.warnings == [
            "Nothing was written in Roman / Latin, so the text is unchanged. "
            "Choose the script the subtitles are written in."
        ]

    def test_converted_text_has_no_warning(self, tmp_path):
        cfg = TransliterateConfig(input_path=_subtitle(tmp_path), source_scheme="roman", target_scheme="ur")
        assert TransliterateTask(cfg).run().warnings == []
