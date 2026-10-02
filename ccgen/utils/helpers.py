# helpers.py - path and formatting utilities for CC-Gen-Ultimate

import os
import sys
from typing import Any

from PySide6.QtCore import QUrl


def resource_path(relative: str) -> str:
    """Return absolute path to a resource; works in dev and PyInstaller builds."""
    try:
        base = getattr(sys, "_MEIPASS", None)
        if base is None:
            here = os.path.dirname(os.path.abspath(__file__))
            base = os.path.dirname(os.path.dirname(here))
        return os.path.normpath(os.path.join(base, relative))
    except Exception:
        return relative


def plural(count: int, noun: str) -> str:
    """Return "1 file" / "3 files" style counts for user-facing messages."""
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def to_local_path(value: Any) -> str:
    """Convert a QUrl, file:// URL string, or plain path into a normalized local path."""
    if hasattr(value, "toLocalFile"):
        text = value.toLocalFile() or value.toString()
    else:
        text = str(value)
        if text.startswith("file:"):
            text = QUrl(text).toLocalFile()
    return os.path.normpath(text) if text else ""


def format_seconds(seconds: float) -> str:
    """Format float seconds into a human-readable duration string."""
    try:
        secs = int(seconds)
        if secs < 60:
            return f"{secs}s"
        mins, secs = divmod(secs, 60)
        if mins < 60:
            return f"{mins}m {secs}s"
        hrs, mins = divmod(mins, 60)
        return f"{hrs}h {mins}m {secs}s"
    except Exception:
        return "0s"


def ensure_dir(path: str) -> str:
    """Create directory (and parents) if it does not exist. Returns path."""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def safe_stem(path: str) -> str:
    """Return filename without extension from a full path."""
    try:
        return os.path.splitext(os.path.basename(path))[0]
    except Exception:
        return path


def format_bytes(num_bytes: float) -> str:
    """Format a byte count into a human-readable string (e.g. '45.2 MB')."""
    try:
        for unit in ("B", "KB", "MB", "GB"):
            if abs(num_bytes) < 1024.0:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} TB"
    except Exception:
        return "0 B"


def format_duration_ms(seconds: float) -> str:
    """Format float seconds into HH:MM:SS for subtitle segment timestamps."""
    try:
        total = int(seconds)
        hrs, remainder = divmod(total, 3600)
        mins, secs = divmod(remainder, 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    except Exception:
        return "00:00:00"
