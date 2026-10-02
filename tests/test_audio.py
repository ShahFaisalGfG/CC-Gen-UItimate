# test_audio.py - unit tests for ccgen.core.audio (decodes small media files generated per test)

import math
import struct
import wave

import av
import numpy as np
import pytest

from ccgen.config.defaults import AudioDefaults
from ccgen.core.audio import load_audio


def _write_wav(path, seconds: float, rate: int = 44100, channels: int = 2) -> None:
    """Write a 440 Hz 16-bit PCM tone, so tests also cover resampling and downmixing."""
    frames = int(seconds * rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        samples = (int(8000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(frames))
        wav.writeframes(b"".join(struct.pack("<h", s) * channels for s in samples))


def _write_silent_video(path) -> None:
    """Write a short video file that has no audio stream."""
    with av.open(str(path), "w", format="mp4") as container:
        stream = container.add_stream("mpeg4", rate=10)
        stream.width, stream.height, stream.pix_fmt = 32, 32, "yuv420p"
        for _ in range(5):
            frame = av.VideoFrame.from_ndarray(np.zeros((32, 32, 3), dtype=np.uint8), format="rgb24")
            container.mux(stream.encode(frame))
        container.mux(stream.encode())


class TestLoadAudio:
    def test_decodes_to_16k_mono_float32(self, tmp_path):
        path = tmp_path / "tone.wav"
        _write_wav(path, seconds=1.0)

        audio = load_audio(str(path))

        assert audio.dtype == np.float32
        assert audio.ndim == 1
        assert abs(audio.size - AudioDefaults.SAMPLE_RATE) < AudioDefaults.SAMPLE_RATE * 0.02
        assert 0.1 < float(np.abs(audio).max()) <= 1.0

    def test_missing_input_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_audio(str(tmp_path / "nonexistent.mp4"))

    def test_non_media_file_raises_readable_error(self, tmp_path):
        path = tmp_path / "fake.mp4"
        path.write_bytes(b"this is not a video")

        with pytest.raises(RuntimeError, match="fake.mp4 could not be read as audio or video"):
            load_audio(str(path))

    def test_video_without_audio_track_raises_readable_error(self, tmp_path):
        path = tmp_path / "silent.mp4"
        _write_silent_video(path)

        with pytest.raises(RuntimeError, match="silent.mp4 has no audio track"):
            load_audio(str(path))

    def test_empty_audio_raises(self, tmp_path):
        path = tmp_path / "empty.wav"
        _write_wav(path, seconds=0)

        with pytest.raises(RuntimeError, match="empty.wav contains no audio"):
            load_audio(str(path))
