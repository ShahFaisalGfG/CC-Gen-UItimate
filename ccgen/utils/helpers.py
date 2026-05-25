# helpers.py — path and formatting utilities for CC-Gen-Ultimate

import os
import sys


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
