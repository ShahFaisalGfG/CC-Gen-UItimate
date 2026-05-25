# prefs_ctrl.py — preferences controller

from PySide6.QtCore import Property, QObject, Signal, Slot

from ccgen.config.defaults import (
    LanguageOptions,
    LoggingDefaults,
    ModelDefaults,
    TransliterationDefaults,
)
from ccgen.utils.settings import get_default_settings, load_settings, save_settings


class PrefsController(QObject):
    """Exposes application preferences to QML with live change notifications."""

    settingsChanged = Signal()
    themeChanged    = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = load_settings()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _get(self, *keys: str, default=None):
        """Navigate nested settings keys and return the value or default."""
        try:
            val = self._settings
            for k in keys:
                val = val[k]
            return val
        except Exception:
            return default

    def _set(self, value, *keys: str) -> None:
        """Set a nested settings value without saving to disk."""
        try:
            node = self._settings
            for k in keys[:-1]:
                node = node.setdefault(k, {})
            node[keys[-1]] = value
        except Exception:
            pass

    # ── Constant option lists ────────────────────────────────────────────────

    @Property(list, constant=True)
    def themeOptions(self) -> list:
        """Theme choices exposed to QML."""
        return ["System", "Light", "Dark"]

    @Property(list, constant=True)
    def modelOptions(self) -> list:
        """Whisper model names exposed to QML."""
        return ModelDefaults.SUPPORTED_MODELS

    @Property(list, constant=True)
    def languageOptions(self) -> list:
        """Transcription language options as list of {label, code} dicts."""
        return [
            {"label": label, "code": code if code else ""}
            for label, code in LanguageOptions.TRANSCRIPTION
        ]

    @Property(list, constant=True)
    def targetOptions(self) -> list:
        """Translation target language options as list of {label, code} dicts."""
        return [
            {"label": label, "code": code}
            for label, code in LanguageOptions.TRANSLATION_TARGETS
        ]

    @Property(list, constant=True)
    def translitSchemeOptions(self) -> list:
        """Transliteration scheme options as list of {label, code} dicts."""
        return [
            {"label": label, "code": code}
            for label, code in TransliterationDefaults.SCHEMES
        ]

    # ── Persisted settings properties ────────────────────────────────────────

    @Property(str, notify=themeChanged)
    def theme(self) -> str:
        return str(self._get("ui", "theme", default="system"))

    @Property(str, notify=settingsChanged)
    def defaultModel(self) -> str:
        return str(self._get("model", "name", default=ModelDefaults.DEFAULT_MODEL))

    @Property(bool, notify=settingsChanged)
    def enableLogs(self) -> bool:
        return bool(self._get("logging", "enable_logs", default=LoggingDefaults.ENABLE_LOGS))

    @Property(str, notify=settingsChanged)
    def logLevel(self) -> str:
        return str(self._get("logging", "log_level", default=LoggingDefaults.DEFAULT_LOG_LEVEL))

    # ── Slots ────────────────────────────────────────────────────────────────

    @Slot()
    def loadSettings(self) -> None:
        """Reload settings from disk and notify QML."""
        try:
            self._settings = load_settings()
            self.settingsChanged.emit()
        except Exception:
            pass

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value) -> None:
        """Set a dot-separated key and persist immediately."""
        try:
            keys = key.split(".")
            self._set(value, *keys)
            save_settings(self._settings)
            self.settingsChanged.emit()
            if key in ("ui.theme", "theme"):
                self.themeChanged.emit(str(value))
        except Exception:
            pass

    @Slot()
    def resetDefaults(self) -> None:
        """Reset all settings to factory defaults and persist."""
        try:
            self._settings = get_default_settings()
            save_settings(self._settings)
            self.settingsChanged.emit()
            self.themeChanged.emit(self._settings.get("ui", {}).get("theme", "system"))
        except Exception:
            pass
