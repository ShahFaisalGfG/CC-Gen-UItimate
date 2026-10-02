# test_task_outputs.py - unit tests for output naming and engine capability checks

import os

import pytest

from ccgen.config.capabilities import language_from_filename, neural_model_key, transliteration_supported
from ccgen.core.tasks.outputs import output_base, output_path


class TestLanguageFromFilename:
    @pytest.mark.parametrize("name, expected", [
        ("movie_ur.srt", "ur"),
        ("Movie_EN.vtt", "en"),
        ("movie.srt", ""),
        ("movie_xx.srt", ""),
        ("my_movie.srt", ""),
        ("movie_tr_ur_roman.srt", ""),
    ])
    def test_reads_known_suffixes_only(self, name, expected):
        assert language_from_filename(os.path.join("dir", name)) == expected


class TestOutputNaming:
    def test_subtitle_language_suffix_is_replaced(self):
        assert output_base(os.path.join("d", "movie_en.srt")) == os.path.join("d", "movie.srt")

    def test_media_names_are_kept_whole(self):
        assert output_base(os.path.join("d", "talk_en.mp4")) == os.path.join("d", "talk_en.mp4")

    def test_output_dir_relocates_file(self):
        path = output_path(os.path.join("src", "movie_en.srt"), "_ur", ".srt", os.path.join("out"))
        assert path == os.path.join("out", "movie_ur.srt")


class TestTransliterationSupport:
    def test_rule_engine_handles_any_two_known_scripts(self):
        assert transliteration_supported("rule", "ta", "ur")
        assert not transliteration_supported("rule", "ur", "ur")
        assert not transliteration_supported("rule", "klingon", "ur")

    def test_neural_engine_handles_its_model_pairs(self):
        assert neural_model_key("ur", "roman") == "ur-roman"
        assert neural_model_key("pa", "ur") == "hi-ur"
        assert transliteration_supported("neural", "roman", "ur")
        assert not transliteration_supported("neural", "ur", "hi")

    def test_unknown_engine_supports_nothing(self):
        assert not transliteration_supported("magic", "ur", "roman")
