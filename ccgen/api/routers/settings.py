# settings.py - routes for reading and updating persisted app settings

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from ccgen.api.schemas.settings import SettingsBatchPayload, SettingsPayload
from ccgen.api.services import settings_service

_log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/settings")
def get_settings() -> dict[str, Any]:
    """Return the full persisted settings dictionary."""
    try:
        return settings_service.get_all()
    except Exception as e:
        _log.error("Failed to load settings: %r", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/settings")
def put_setting(payload: SettingsPayload) -> dict[str, Any]:
    """Update one dot-separated settings key and persist it immediately."""
    try:
        return settings_service.set_one(payload.key, payload.value)
    except Exception as e:
        _log.error("Failed to update setting %s: %r", payload.key, e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/settings")
def patch_settings(payload: SettingsBatchPayload) -> dict[str, Any]:
    """Update several dot-separated keys in one atomic save (used by the Preferences window)."""
    try:
        return settings_service.set_many(payload.values)
    except Exception as e:
        _log.error("Failed to update settings %s: %r", list(payload.values), e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/settings/reset")
def reset_settings() -> dict[str, Any]:
    """Reset all settings to factory defaults and persist them."""
    try:
        return settings_service.reset_defaults()
    except Exception as e:
        _log.error("Failed to reset settings: %r", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
