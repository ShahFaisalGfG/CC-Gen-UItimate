# test_subtitle.py — unit tests for ccgen.core.subtitle

import os

import pytest

from ccgen.core.subtitle import derive_output_path, write_srt, write_vtt


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


class TestDeriveOutputPath:
    def test_replaces_extension(self):
        result = derive_output_path("/videos/movie.mp4", "", ".srt")
        assert result == "/videos/movie.srt"

    def test_adds_suffix(self):
        result = derive_output_path("/videos/movie.mp4", "_ar", ".srt")
        assert result == "/videos/movie_ar.srt"
