# settings_service.py - serialized read-modify-write access to persisted settings for the API layer

import threading
from typing import Any

from ccgen.config.defaults import get_default_settings
from ccgen.utils.logging import configure_from_settings
from ccgen.utils.settings import load_settings, save_settings

# FastAPI runs sync route handlers on a thread pool, so two saves arriving together would
# otherwise both load the old file and the later write would silently drop the earlier change.
_lock = threading.Lock()


def get_all() -> dict[str, Any]:
    """Return the full persisted settings dictionary."""
    with _lock:
        return load_settings()


def reset_defaults() -> dict[str, Any]:
    """Overwrite persisted settings with factory defaults and return them."""
    with _lock:
        defaults = get_default_settings()
        _persist(defaults)
        configure_from_settings(defaults)
        return defaults


def set_one(key: str, value: Any) -> dict[str, Any]:
    """Set a dot-separated settings key, persist it, and return the updated dictionary."""
    return set_many({key: value})


def set_many(values: dict[str, Any]) -> dict[str, Any]:
    """Set several dot-separated keys in one atomic save and return the updated dictionary."""
    with _lock:
        settings = load_settings()
        for key, value in values.items():
            _assign(settings, key, value)
        _persist(settings)
        if any(key.startswith("logging.") for key in values):
            configure_from_settings(settings)
        return settings


def _assign(settings: dict[str, Any], key: str, value: Any) -> None:
    """Write `value` at a dot-separated path, creating intermediate sections as needed."""
    node = settings
    parts = key.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = node[part] = {}
        node = child
    node[parts[-1]] = value


def _persist(settings: dict[str, Any]) -> None:
    """Save settings, raising so the route reports a failed write instead of a silent success."""
    if not save_settings(settings):
        raise OSError("Could not write the settings file.")
