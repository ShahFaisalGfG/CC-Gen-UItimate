# subtitle_parser.py — parse SRT and VTT files into Segment lists

import logging
import os
import re

from ccgen.core import Segment

_log = logging.getLogger(__name__)

_SUBTITLE_EXTS = frozenset({".srt", ".vtt"})
_ARROW = re.compile(r"\s*-->\s*")


def parse_subtitle(path: str) -> list[Segment]:
    """Detect file type and parse SRT or VTT into a Segment list."""
    try:
        ext = os.path.splitext(path)[1].lower()
        _log.info("Parsing subtitle file: %s (%s)", os.path.basename(path), ext)
        if ext == ".srt":
            segments = _parse_srt(path)
        elif ext == ".vtt":
            segments = _parse_vtt(path)
        else:
            raise ValueError(f"Unsupported subtitle extension: {ext!r}")
        _log.info("Parsed %d segments from %s", len(segments), os.path.basename(path))
        return segments
    except (OSError, ValueError):
        raise
    except Exception as e:
        _log.error("Subtitle parse failed for %s: %r", path, e, exc_info=True)
        raise OSError(f"Subtitle parse failed: {e}") from e


def is_subtitle(path: str) -> bool:
    """Return True when the path points to a recognised subtitle file."""
    return os.path.splitext(path)[1].lower() in _SUBTITLE_EXTS


def _parse_srt(path: str) -> list[Segment]:
    """Parse an SRT file into a list of Segments."""
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    segments: list[Segment] = []
    for idx, block in enumerate(_split_blocks(text)):
        seg = _build_segment(idx, block, comma_sep=True)
        if seg:
            segments.append(seg)
    return segments


def _parse_vtt(path: str) -> list[Segment]:
    """Parse a WebVTT file into a list of Segments."""
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    # strip WEBVTT header line and any leading NOTE / STYLE / REGION blocks
    lines = text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if "-->" in ln or re.match(r"^\d", ln.strip())),
        1,
    )
    segments: list[Segment] = []
    for idx, block in enumerate(_split_blocks("\n".join(lines[start:]))):
        seg = _build_segment(idx, block, comma_sep=False)
        if seg:
            segments.append(seg)
    return segments


def _split_blocks(text: str) -> list[list[str]]:
    """Split raw subtitle text into non-empty line groups."""
    blocks: list[list[str]] = []
    for raw in re.split(r"\n{2,}", text.strip()):
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if lines:
            blocks.append(lines)
    return blocks


def _build_segment(idx: int, lines: list[str], comma_sep: bool) -> Segment | None:
    """Build a Segment from a subtitle block; return None when timestamp is missing."""
    time_line = _find_timestamp_line(lines)
    if time_line is None:
        return None
    parts = _ARROW.split(lines[time_line], maxsplit=1)
    if len(parts) != 2:
        return None
    start = _to_seconds(parts[0], comma_sep)
    end   = _to_seconds(parts[1].split()[0], comma_sep)  # drop optional cue settings
    body  = " ".join(lines[time_line + 1:])
    if not body:
        return None
    return Segment(id=idx, start=start, end=end, text=body, words=[], language="")


def _find_timestamp_line(lines: list[str]) -> int | None:
    """Return the index of the first line containing '-->'."""
    for i, ln in enumerate(lines):
        if "-->" in ln:
            return i
    return None


def _to_seconds(ts: str, comma_sep: bool) -> float:
    """Convert 'HH:MM:SS,mmm' or 'HH:MM:SS.mmm' or 'MM:SS.mmm' to float seconds."""
    try:
        ts = ts.strip().replace(",", ".")
        parts = ts.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(ts)
    except Exception:
        return 0.0
