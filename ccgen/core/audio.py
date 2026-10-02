# audio.py - decode the audio track of any video or audio file into mono samples
#
# Decoding runs in-process through PyAV (the FFmpeg libraries bundled with faster-whisper),
# so the app needs no separate ffmpeg install, no subprocess, and no temporary WAV file.

import os
from typing import cast

import numpy as np
from av import FFmpegError
from faster_whisper.audio import decode_audio

from ccgen.config.defaults import AudioDefaults


def load_audio(input_path: str, sample_rate: int = AudioDefaults.SAMPLE_RATE) -> np.ndarray:
    """Return the file's audio as mono float32 samples at `sample_rate` (16 kHz for Whisper).

    Raises FileNotFoundError for a missing file and RuntimeError with a readable message when
    the file has no audio track or is not a media file.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    name = os.path.basename(input_path)
    try:
        # decode_audio returns a (left, right) tuple only when split_stereo=True.
        audio = cast(np.ndarray, decode_audio(input_path, sampling_rate=sample_rate))
    except IndexError as e:
        # PyAV raises IndexError when the container has no audio stream (e.g. a silent video).
        raise RuntimeError(f"{name} has no audio track.") from e
    except FFmpegError as e:
        raise RuntimeError(f"{name} could not be read as audio or video ({e.strerror or e}).") from e
    if audio.size == 0:
        raise RuntimeError(f"{name} contains no audio.")
    return audio
