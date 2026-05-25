# logging.py — log file management for CC-Gen-Ultimate

import os
import sys
from datetime import datetime


def get_logs_dir() -> str:
    """Return the logs directory path, creating it if needed."""
    try:
        if getattr(sys, "frozen", False):
            appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
            logs_dir = os.path.join(appdata, "CC-Gen-Ultimate", "logs")
            os.makedirs(logs_dir, exist_ok=True)
            return logs_dir
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    logs_dir = os.path.join(root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def write_log(message: str) -> None:
    """Append a timestamped log entry to ccgen.log."""
    try:
        log_file = os.path.join(get_logs_dir(), "ccgen.log")
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] {message}\n")
    except Exception:
        pass
