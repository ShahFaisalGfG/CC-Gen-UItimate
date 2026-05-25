# audio.py — audio extraction from video/audio files via ffmpeg-python

import os
import shutil
import tempfile
from typing import Optional

import ffmpeg

from ccgen.config.defaults import AudioDefaults


def extract_audio(input_path: str, output_path: Optional[str] = None) -> str:
    """Extract a 16 kHz mono WAV from any video/audio file. Returns output path.

    Creates a temporary file when output_path is None; caller must delete it via cleanup_temp().
    """
    try:
        _validate_input(input_path)
        _check_ffmpeg()
        wav_path = output_path or _make_temp_wav()
        _run_ffmpeg(input_path, wav_path)
        return wav_path
    except (FileNotFoundError, RuntimeError):
        raise
    except Exception as e:
        raise RuntimeError(f"Audio extraction failed: {e}") from e


def cleanup_temp(path: str) -> None:
    """Delete a temporary audio file, silently ignoring any errors."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _validate_input(path: str) -> None:
    """Raise FileNotFoundError when the input path does not exist."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Input file not found: {path}")


def _check_ffmpeg() -> None:
    """Raise RuntimeError when ffmpeg binary is not available on PATH."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. "
            "It should have been installed by the CC-Gen-Ultimate installer."
        )


def _make_temp_wav() -> str:
    """Create and return the path to a new temporary WAV file."""
    try:
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="ccgen_audio_")
        os.close(fd)
        return path
    except Exception as e:
        raise RuntimeError(f"Cannot create temporary file: {e}") from e


def _run_ffmpeg(input_path: str, output_path: str) -> None:
    """Execute ffmpeg to convert input to 16 kHz mono PCM WAV.

    Wraps ffmpeg.Error into RuntimeError with the original stderr message.
    """
    try:
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                ar=AudioDefaults.SAMPLE_RATE,
                ac=AudioDefaults.CHANNELS,
                format=AudioDefaults.AUDIO_FORMAT,
                acodec="pcm_s16le",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else str(e)
        raise RuntimeError(f"ffmpeg error: {stderr}") from e
