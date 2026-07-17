# settings.py — request contract for updating a single persisted setting

from typing import Any

from pydantic import BaseModel


class SettingsPayload(BaseModel):
    """A dot-separated settings key and its new value, mirrors the prior setSetting() slot."""

    key: str
    value: Any
