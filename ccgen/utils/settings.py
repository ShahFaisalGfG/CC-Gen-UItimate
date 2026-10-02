# settings.py - settings persistence: load, save, and merge

import json
import logging
import os
import sys
from typing import Any

from ccgen.config.defaults import get_default_settings

_log = logging.getLogger(__name__)


def get_settings_file() -> str:
    """Return path to settings.json, creating the app data dir if needed."""
    try:
        if getattr(sys, "frozen", False):
            appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
            data_dir = os.path.join(appdata, "CC-Gen-Ultimate")
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, "settings.json")
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "settings.json")


def load_settings() -> dict[str, Any]:
    """Load settings from disk, merging with defaults for any missing keys."""
    path = get_settings_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                user = json.load(fh)
            return merge_settings(get_default_settings(), user)
        except Exception:
            _log.warning("Settings file %s is unreadable; using defaults", path, exc_info=True)
    return get_default_settings()


def save_settings(settings: dict[str, Any]) -> bool:
    """Persist a settings dictionary to disk atomically. Returns True on success.

    Writes to a temporary file in the same folder and swaps it in, so a crash or a full disk
    mid-write can never leave a truncated settings.json behind.
    """
    path = get_settings_file()
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception:
        _log.error("Failed to save settings to %s", path, exc_info=True)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def merge_settings(
    defaults: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Deep-merge overrides onto defaults, preserving all nested default keys.

    Rebuilds every nested dict fresh (even branches `overrides` never touches), so the
    result never aliases a mutable nested dict from either `defaults` or `overrides`.
    """
    result = {
        key: (merge_settings(value, {}) if isinstance(value, dict) else value)
        for key, value in defaults.items()
    }
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_settings(result[key], value)
        else:
            result[key] = value
    return result
