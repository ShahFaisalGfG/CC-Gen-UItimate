# settings_service.py — thin wrapper over ccgen.utils.settings for the API layer

from typing import Any

from ccgen.config.defaults import get_default_settings
from ccgen.utils.settings import load_settings, save_settings


def get_all() -> dict[str, Any]:
    """Return the full persisted settings dictionary."""
    return load_settings()


def reset_defaults() -> dict[str, Any]:
    """Overwrite persisted settings with factory defaults and return them."""
    defaults = get_default_settings()
    save_settings(defaults)
    return defaults


def set_one(key: str, value: Any) -> dict[str, Any]:
    """Set a dot-separated settings key, persist it, and return the updated dictionary."""
    settings = load_settings()
    node = settings
    parts = key.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    save_settings(settings)
    return settings
