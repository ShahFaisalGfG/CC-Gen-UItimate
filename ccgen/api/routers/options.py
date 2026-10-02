# options.py — route serving option lists that populate UI dropdowns

from fastapi import APIRouter

from ccgen.config.defaults import DubbingDefaults, LanguageOptions, ModelDefaults, TransliterationDefaults
from ccgen.config.voices import VOICES

router = APIRouter()


@router.get("/options")
def get_options() -> dict[str, list]:
    """Return every option list needed to populate the task settings UI."""
    return {
        "models": ModelDefaults.SUPPORTED_MODELS,
        "languages": _as_items(LanguageOptions.TRANSCRIPTION),
        "translation_targets": _as_items(LanguageOptions.TRANSLATION_TARGETS),
        "translit_schemes": _as_items(TransliterationDefaults.SCHEMES),
        "translit_engines": _as_items(TransliterationDefaults.ENGINES),
        "dub_modes": [{"label": label, "code": code, "hint": hint} for label, code, hint in DubbingDefaults.MODES],
        "dub_languages": _as_items(DubbingDefaults.LANGUAGES),
        "voices": [
            {"key": v.key, "engine": v.engine, "language": v.language, "label": v.label} for v in VOICES
        ],
    }


def _as_items(pairs: list) -> list[dict[str, str]]:
    """Convert (label, code) tuples into {label, code} dicts for JSON responses."""
    return [{"label": label, "code": code or ""} for label, code in pairs]
