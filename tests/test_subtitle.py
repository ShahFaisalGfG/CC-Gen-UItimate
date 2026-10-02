# test_subtitle.py - unit tests for ccgen.core.subtitle

import os

import pytest

from ccgen.core import Segment

from ccgen.core.subtitle import derive_output_path, wrap_text, write_ass, write_lrc, write_sbv, write_srt, write_vtt


class TestWriteSrt:
    def test_creates_srt_file(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.srt")
        result = write_srt(sample_segments, out)
        assert result == out
        assert os.path.exists(out)

    def test_srt_contains_sequence_numbers(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.srt")
        write_srt(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert "1\n" in content
        assert "2\n" in content

    def test_srt_timestamp_format(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.srt")
        write_srt(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert "00:00:00,000 --> 00:00:03,500" in content

    def test_translated_uses_translated_field(self, tmp_path, sample_translated_segments):
        out = str(tmp_path / "output_es.srt")
        write_srt(sample_translated_segments, out, translated=True)
        content = open(out, encoding="utf-8").read()
        assert "Hola mundo" in content

    def test_write_fails_on_bad_path(self, sample_segments):
        with pytest.raises(OSError):
            write_srt(sample_segments, "/nonexistent/dir/output.srt")


class TestWriteVtt:
    def test_creates_vtt_file(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.vtt")
        result = write_vtt(sample_segments, out)
        assert result == out
        assert os.path.exists(out)

    def test_vtt_header_present(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.vtt")
        write_vtt(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert content.startswith("WEBVTT")

    def test_vtt_uses_dot_separator(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.vtt")
        write_vtt(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert "00:00:00.000 --> 00:00:03.500" in content


class TestWriteLrc:
    def test_creates_lrc_file(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.lrc")
        result = write_lrc(sample_segments, out)
        assert result == out
        assert os.path.exists(out)

    def test_lrc_timestamp_format(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.lrc")
        write_lrc(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert "[00:00.00]" in content
        assert "[00:04.00]" in content

    def test_lrc_has_no_end_time_or_sequence_numbers(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.lrc")
        write_lrc(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert "-->" not in content
        assert content.strip().startswith("[")

    def test_translated_uses_translated_field(self, tmp_path, sample_translated_segments):
        out = str(tmp_path / "output_es.lrc")
        write_lrc(sample_translated_segments, out, translated=True)
        content = open(out, encoding="utf-8").read()
        assert "Hola mundo" in content


class TestWriteAss:
    def test_creates_ass_file(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.ass")
        result = write_ass(sample_segments, out)
        assert result == out
        assert os.path.exists(out)

    def test_ass_header_sections_present(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.ass")
        write_ass(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content

    def test_ass_dialogue_timestamp_format(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.ass")
        write_ass(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert "Dialogue: 0,0:00:00.00,0:00:03.50,Default" in content

    def test_translated_uses_translated_field(self, tmp_path, sample_translated_segments):
        out = str(tmp_path / "output_es.ass")
        write_ass(sample_translated_segments, out, translated=True)
        content = open(out, encoding="utf-8").read()
        assert "Hola mundo" in content


class TestWriteSbv:
    def test_creates_sbv_file(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.sbv")
        result = write_sbv(sample_segments, out)
        assert result == out
        assert os.path.exists(out)

    def test_sbv_uses_comma_separated_timestamps(self, tmp_path, sample_segments):
        out = str(tmp_path / "output.sbv")
        write_sbv(sample_segments, out)
        content = open(out, encoding="utf-8").read()
        assert "0:00:00.000,0:00:03.500" in content
        assert "-->" not in content

    def test_translated_uses_translated_field(self, tmp_path, sample_translated_segments):
        out = str(tmp_path / "output_es.sbv")
        write_sbv(sample_translated_segments, out, translated=True)
        content = open(out, encoding="utf-8").read()
        assert "Hola mundo" in content


class TestDeriveOutputPath:
    def test_replaces_extension(self):
        result = derive_output_path("/videos/movie.mp4", "", ".srt")
        assert result == "/videos/movie.srt"

    def test_adds_suffix(self):
        result = derive_output_path("/videos/movie.mp4", "_ar", ".srt")
        assert result == "/videos/movie_ar.srt"


class TestWrapText:
    def test_short_text_stays_on_one_line(self):
        assert wrap_text("Hello there", 42, 2) == ["Hello there"]

    def test_two_lines_are_balanced(self):
        lines = wrap_text("one two three four five six seven eight nine ten eleven", 42, 2)
        assert len(lines) == 2
        assert abs(len(lines[0]) - len(lines[1])) <= 10

    def test_overflow_keeps_every_word(self):
        text = " ".join(f"word{i}" for i in range(40))
        lines = wrap_text(text, 42, 2)
        assert " ".join(lines) == text
        assert all(len(line) <= 42 for line in lines)

    def test_unbroken_text_is_chunked(self):
        lines = wrap_text("x" * 50, 20, 2)
        assert "".join(lines) == "x" * 50
        assert all(len(line) <= 20 for line in lines)

    def test_blank_text_has_no_lines(self):
        assert wrap_text("   ", 42, 2) == []


class TestCueNumberingAndEscaping:
    def test_srt_numbers_are_sequential_after_skipping_empty_cues(self, tmp_path):
        segments: list[Segment] = [
            {"id": 3, "start": 0.0, "end": 1.0, "text": "first", "words": [], "language": "en"},
            {"id": 7, "start": 1.0, "end": 2.0, "text": "  ", "words": [], "language": "en"},
            {"id": 9, "start": 2.0, "end": 3.0, "text": "second", "words": [], "language": "en"},
        ]
        out = str(tmp_path / "out.srt")
        write_srt(segments, out)
        blocks = open(out, encoding="utf-8").read().strip().split("\n\n")
        assert [block.splitlines()[0] for block in blocks] == ["1", "2"]

    def test_vtt_escapes_markup_characters(self, tmp_path):
        segments: list[Segment] = [{"id": 0, "start": 0.0, "end": 1.0, "text": "a < b & c", "words": [], "language": "en"}]
        out = str(tmp_path / "out.vtt")
        write_vtt(segments, out)
        assert "a &lt; b &amp; c" in open(out, encoding="utf-8").read()

    def test_long_cue_text_is_never_truncated(self, tmp_path):
        text = " ".join(f"word{i}" for i in range(40))
        segments: list[Segment] = [{"id": 0, "start": 0.0, "end": 5.0, "text": text, "words": [], "language": "en"}]
        out = str(tmp_path / "out.srt")
        write_srt(segments, out)
        assert "word39" in open(out, encoding="utf-8").read()
