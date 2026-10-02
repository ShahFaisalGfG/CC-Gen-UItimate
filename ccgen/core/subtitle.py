# subtitle.py - SRT, VTT, LRC, ASS, and SBV subtitle generation from timestamped segment data

import math
import os
from typing import Iterator, Optional, Union

from ccgen.config.defaults import OutputDefaults
from ccgen.core import AnySegment, Segment, TranslatedSegment, TransliteratedSegment

SubtitleSource = Union[list[Segment], list[TranslatedSegment], list[TransliteratedSegment]]


def write_srt(
    segments: SubtitleSource,
    output_path: str,
    translated: bool = False,
    max_line_length: int = OutputDefaults.MAX_LINE_LENGTH,
    max_lines: int = OutputDefaults.MAX_LINES,
) -> str:
    """Write an SRT subtitle file from segments. Returns output_path.

    Uses the 'translated' field when translated=True, otherwise uses 'text'.
    """
    try:
        lines = _build_srt(segments, translated, (max_line_length, max_lines))
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
    max_line_length: int = OutputDefaults.MAX_LINE_LENGTH,
    max_lines: int = OutputDefaults.MAX_LINES,
) -> str:
    """Write a WebVTT subtitle file from segments. Returns output_path.

    Uses the 'translated' field when translated=True, otherwise uses 'text'.
    """
    try:
        lines = ["WEBVTT", ""] + _build_vtt_cues(segments, translated, (max_line_length, max_lines))
        _write_file(output_path, lines)
        return output_path
    except OSError:
        raise
    except Exception as e:
        raise OSError(f"VTT write failed: {e}") from e


def write_lrc(
    segments: SubtitleSource,
    output_path: str,
    translated: bool = False,
    max_line_length: int = OutputDefaults.MAX_LINE_LENGTH,
    max_lines: int = OutputDefaults.MAX_LINES,
) -> str:
    """Write an LRC lyrics-style subtitle file from segments. Returns output_path.

    LRC has no end-time field, so it carries only each segment's start time, and each cue is
    written as one line since LRC readers show one line per timestamp.
    """
    try:
        lines = _build_lrc_lines(segments, translated)
        _write_file(output_path, lines)
        return output_path
    except OSError:
        raise
    except Exception as e:
        raise OSError(f"LRC write failed: {e}") from e


def write_ass(
    segments: SubtitleSource,
    output_path: str,
    translated: bool = False,
    max_line_length: int = OutputDefaults.MAX_LINE_LENGTH,
    max_lines: int = OutputDefaults.MAX_LINES,
) -> str:
    """Write an ASS (Advanced SubStation Alpha) subtitle file from segments. Returns output_path.

    Uses one default style; wrapped lines are joined with the ASS forced line-break `\\N`.
    """
    try:
        lines = _ASS_HEADER + _build_ass_events(segments, translated, (max_line_length, max_lines))
        _write_file(output_path, lines)
        return output_path
    except OSError:
        raise
    except Exception as e:
        raise OSError(f"ASS write failed: {e}") from e


def write_sbv(
    segments: SubtitleSource,
    output_path: str,
    translated: bool = False,
    max_line_length: int = OutputDefaults.MAX_LINE_LENGTH,
    max_lines: int = OutputDefaults.MAX_LINES,
) -> str:
    """Write a YouTube SBV subtitle file from segments. Returns output_path.

    Uses the 'translated' field when translated=True, otherwise uses 'text'.
    """
    try:
        lines = _build_sbv_cues(segments, translated, (max_line_length, max_lines))
        _write_file(output_path, lines)
        return output_path
    except OSError:
        raise
    except Exception as e:
        raise OSError(f"SBV write failed: {e}") from e


def derive_output_path(input_path: str, suffix: str, ext: str) -> str:
    """Build an output path from the input file path, a suffix, and extension.

    Example: /videos/movie.mp4 + '_ar' + '.srt'  →  /videos/movie_ar.srt
    """
    base = os.path.splitext(input_path)[0]
    return f"{base}{suffix}{ext}"


LineLimits = tuple[int, int]


def _build_srt(segments: SubtitleSource, translated: bool, limits: LineLimits) -> list[str]:
    """Return SRT-formatted text lines, numbering cues 1..n with no gaps."""
    lines: list[str] = []
    for number, (seg, text_lines) in enumerate(_cues_with_text(segments, translated, limits), 1):
        lines.append(str(number))
        lines.append(f"{_srt_time(seg['start'])} --> {_srt_time(seg['end'])}")
        lines.extend(text_lines)
        lines.append("")
    return lines


def _build_vtt_cues(segments: SubtitleSource, translated: bool, limits: LineLimits) -> list[str]:
    """Return VTT cue lines, escaping the characters WebVTT reserves for markup."""
    lines: list[str] = []
    for seg, text_lines in _cues_with_text(segments, translated, limits):
        lines.append(f"{_vtt_time(seg['start'])} --> {_vtt_time(seg['end'])}")
        lines.extend(_vtt_escape(line) for line in text_lines)
        lines.append("")
    return lines


def _build_lrc_lines(segments: SubtitleSource, translated: bool) -> list[str]:
    """Return one '[mm:ss.xx]text' line per segment (LRC readers show one line per timestamp)."""
    lines: list[str] = []
    for seg in segments:  # type: ignore[union-attr]
        text = _get_text(seg, translated)
        if not text:
            continue
        lines.append(f"[{_lrc_time(seg['start'])}]{text}")
    return lines


def _build_sbv_cues(segments: SubtitleSource, translated: bool, limits: LineLimits) -> list[str]:
    """Return SBV cue lines for all segments."""
    lines: list[str] = []
    for seg, text_lines in _cues_with_text(segments, translated, limits):
        lines.append(f"{_sbv_time(seg['start'])},{_sbv_time(seg['end'])}")
        lines.extend(text_lines)
        lines.append("")
    return lines


_ASS_HEADER = [
    "[Script Info]",
    "Title: CC-Gen-Ultimate subtitle export",
    "ScriptType: v4.00+",
    "WrapStyle: 0",
    "ScaledBorderAndShadow: yes",
    "YCbCr Matrix: None",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
    "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
    "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
]


def _build_ass_events(segments: SubtitleSource, translated: bool, limits: LineLimits) -> list[str]:
    """Return one ASS 'Dialogue:' line per segment, with wrapped lines joined by \\N."""
    lines: list[str] = []
    for seg, text_lines in _cues_with_text(segments, translated, limits):
        text = "\\N".join(text_lines)
        start, end = _ass_time(seg["start"]), _ass_time(seg["end"])
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    return lines


def _get_text(seg: Union[Segment, TranslatedSegment, TransliteratedSegment], translated: bool) -> str:
    """Extract the appropriate text field from any segment dict."""
    if "transliterated" in seg:
        return seg["transliterated"].strip()  # type: ignore[typeddict-item]
    if translated and "translated" in seg:
        return seg["translated"].strip()  # type: ignore[typeddict-item]
    return seg.get("text", "").strip()  # type: ignore[union-attr]


def _cues_with_text(
    segments: SubtitleSource,
    translated: bool,
    limits: LineLimits,
) -> Iterator[tuple[AnySegment, list[str]]]:
    """Yield each segment with its wrapped text lines, skipping segments with no text."""
    for seg in segments:  # type: ignore[union-attr]
        text_lines = wrap_text(_get_text(seg, translated), *limits)
        if text_lines:
            yield seg, text_lines


def wrap_text(text: str, max_len: int = OutputDefaults.MAX_LINE_LENGTH, max_lines: int = OutputDefaults.MAX_LINES) -> list[str]:
    """Break text into display lines of at most max_len characters, never dropping words.

    Text that fits on max_lines lines is split into lines of similar length (a short top line
    over a long bottom line reads awkwardly), preferring a break right after punctuation. Text
    too long for max_lines keeps every word on extra lines rather than losing dialogue.
    """
    text = " ".join(text.split())
    if not text:
        return []
    if len(text) <= max_len:
        return [text]
    words = text.split(" ")
    if len(words) == 1:
        return _chunk(text, max_len)
    if max_lines >= 2 and len(text) <= max_len * 2 + 1:
        balanced = _balanced_split(words, max_len)
        if balanced:
            return balanced
    return _greedy_wrap(words, max_len)


def _balanced_split(words: list[str], max_len: int) -> list[str]:
    """Split words into two lines that both fit, choosing the most even, best-punctuated break."""
    best: Optional[tuple[float, list[str]]] = None
    for idx in range(1, len(words)):
        top, bottom = " ".join(words[:idx]), " ".join(words[idx:])
        if len(top) > max_len or len(bottom) > max_len:
            continue
        score = float(abs(len(top) - len(bottom)))
        if words[idx - 1].endswith((".", ",", "?", "!", ";", ":")):
            score -= max_len * 0.25
        if len(top) > len(bottom):
            score += 2  # prefer the bottom line to be the longer one
        if best is None or score < best[0]:
            best = (score, [top, bottom])
    return best[1] if best else []


def _greedy_wrap(words: list[str], max_len: int) -> list[str]:
    """Fill lines word by word; a single word longer than max_len is split into chunks."""
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_len:
            current = candidate
            continue
        if current:
            lines.append(current)
        if len(word) > max_len:
            *full, current = _chunk(word, max_len)
            lines.extend(full)
        else:
            current = word
    if current:
        lines.append(current)
    return lines


def _chunk(text: str, max_len: int) -> list[str]:
    """Split unbroken text (e.g. Chinese or Japanese) into evenly sized lines."""
    count = math.ceil(len(text) / max_len)
    size = math.ceil(len(text) / count)
    return [text[i:i + size] for i in range(0, len(text), size)]


def _vtt_escape(line: str) -> str:
    """Escape the characters WebVTT cue text treats as markup."""
    return line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def _lrc_time(seconds: float) -> str:
    """Convert seconds to LRC timestamp format mm:ss.xx (centiseconds)."""
    cs = int(round(seconds * 100))
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{m:02d}:{s:02d}.{cs:02d}"


def _sbv_time(seconds: float) -> str:
    """Convert seconds to SBV timestamp format H:MM:SS.mmm (hours not zero-padded)."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h}:{m:02d}:{s:02d}.{ms:03d}"


def _ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format H:MM:SS.cc (centiseconds, hours not zero-padded)."""
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _write_file(path: str, lines: list[str]) -> None:
    """Write joined lines to a UTF-8 text file."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
