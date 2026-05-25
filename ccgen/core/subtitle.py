# subtitle.py — SRT and VTT subtitle generation from timestamped segment data

import os
from typing import Union

from ccgen.config.defaults import OutputDefaults
from ccgen.core import Segment, TranslatedSegment

SubtitleSource = Union[list[Segment], list[TranslatedSegment]]


def write_srt(
    segments: SubtitleSource,
    output_path: str,
    translated: bool = False,
) -> str:
    """Write an SRT subtitle file from segments. Returns output_path.

    Uses the 'translated' field when translated=True, otherwise uses 'text'.
    """
    try:
        lines = _build_srt(segments, translated)
        _write_file(output_path, lines)
        return output_path
    except OSError:
        raise
    except Exception as e:
        raise OSError(f"SRT write failed: {e}") from e


def write_vtt(
    segments: SubtitleSource,
    output_path: str,
    translated: bool = False,
) -> str:
    """Write a WebVTT subtitle file from segments. Returns output_path.

    Uses the 'translated' field when translated=True, otherwise uses 'text'.
    """
    try:
        lines = ["WEBVTT", ""] + _build_vtt_cues(segments, translated)
        _write_file(output_path, lines)
        return output_path
    except OSError:
        raise
    except Exception as e:
        raise OSError(f"VTT write failed: {e}") from e


def derive_output_path(input_path: str, suffix: str, ext: str) -> str:
    """Build an output path from the input file path, a suffix, and extension.

    Example: /videos/movie.mp4 + '_ar' + '.srt'  →  /videos/movie_ar.srt
    """
    base = os.path.splitext(input_path)[0]
    return f"{base}{suffix}{ext}"


def _build_srt(segments: SubtitleSource, translated: bool) -> list[str]:
    """Return SRT-formatted text lines for all segments."""
    lines: list[str] = []
    for seg in segments:
        lines.append(str(seg["id"] + 1))
        lines.append(f"{_srt_time(seg['start'])} --> {_srt_time(seg['end'])}")
        lines.extend(_wrap_text(_get_text(seg, translated)))
        lines.append("")
    return lines


def _build_vtt_cues(segments: SubtitleSource, translated: bool) -> list[str]:
    """Return VTT cue lines for all segments."""
    lines: list[str] = []
    for seg in segments:
        lines.append(f"{_vtt_time(seg['start'])} --> {_vtt_time(seg['end'])}")
        lines.extend(_wrap_text(_get_text(seg, translated)))
        lines.append("")
    return lines


def _get_text(seg: Union[Segment, TranslatedSegment], translated: bool) -> str:
    """Extract the appropriate text field from a segment dict."""
    if translated and "translated" in seg:
        return seg["translated"].strip()  # type: ignore[typeddict-item]
    return seg["text"].strip()  # type: ignore[typeddict-item]


def _wrap_text(text: str) -> list[str]:
    """Break text into lines within MAX_LINE_LENGTH, capped at MAX_LINES."""
    max_len = OutputDefaults.MAX_LINE_LENGTH
    max_lines = OutputDefaults.MAX_LINES
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            current = ""
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines if lines else [text]


def _srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_time(seconds: float) -> str:
    """Convert seconds to WebVTT timestamp format HH:MM:SS.mmm."""
    return _srt_time(seconds).replace(",", ".")


def _write_file(path: str, lines: list[str]) -> None:
    """Write joined lines to a UTF-8 text file."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
