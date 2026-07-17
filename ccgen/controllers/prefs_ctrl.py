# prefs_ctrl.py — preferences controller (HTTP client of the embedded API)

import json
from typing import Any

from PySide6.QtCore import Property, QByteArray, QObject, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from ccgen.config.defaults import (
    LanguageOptions,
    LoggingDefaults,
    ModelDefaults,
    TransliterationDefaults,
    get_default_settings,
)


class PrefsController(QObject):
    """Exposes application preferences to QML, backed by the embedded API's /settings route."""

    settingsChanged = Signal()
    themeChanged    = Signal(str)

    def __init__(self, base_url: str, parent=None):
        super().__init__(parent)
        self._base_url = base_url
        self._net = QNetworkAccessManager(self)
        self._settings: dict[str, Any] = get_default_settings()
        self._fetch_settings()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _get(self, *keys: str, default=None):
        """Navigate nested settings keys and return the value or default."""
        try:
            val: Any = self._settings
            for k in keys:
                val = val[k]
            return val
        except Exception:
            return default

    def _fetch_settings(self) -> None:
        """Asynchronously fetch the current settings from the embedded API."""
        request = QNetworkRequest(QUrl(f"{self._base_url}/settings"))
        reply = self._net.get(request)
        reply.finished.connect(lambda: self._on_settings_fetched(reply))

    def _on_settings_fetched(self, reply: QNetworkReply) -> None:
        """Apply the fetched settings dictionary and notify QML."""
        try:
            reply.deleteLater()
            if reply.error() != QNetworkReply.NetworkError.NoError:
                return
            self._settings = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
            self.settingsChanged.emit()
            self.themeChanged.emit(str(self._get("ui", "theme", default="system")))
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

    @Property(list, constant=True)
    def translitEngineOptions(self) -> list:
        """Transliteration engine options as list of {label, code} dicts."""
        return [
            {"label": label, "code": code}
            for label, code in TransliterationDefaults.ENGINES
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

    @Property(bool, notify=settingsChanged)
    def defaultEmitSrt(self) -> bool:
        return bool(self._get("output", "srt", default=True))

    @Property(bool, notify=settingsChanged)
    def defaultEmitVtt(self) -> bool:
        return bool(self._get("output", "vtt", default=False))

    @Property(bool, notify=settingsChanged)
    def defaultTranslateEnabled(self) -> bool:
        return bool(self._get("translation", "enabled", default=False))

    @Property(str, notify=settingsChanged)
    def defaultTranslateTarget(self) -> str:
        return str(self._get("translation", "target_lang", default="en"))

    @Property(bool, notify=settingsChanged)
    def defaultTransliterateEnabled(self) -> bool:
        return bool(self._get("transliteration", "enabled", default=False))

    @Property(str, notify=settingsChanged)
    def defaultTranslitSource(self) -> str:
        return str(self._get("transliteration", "source", default="roman"))

    @Property(str, notify=settingsChanged)
    def defaultTranslitTarget(self) -> str:
        return str(self._get("transliteration", "target", default="ur"))

    @Property(str, notify=settingsChanged)
    def defaultTranslitInput(self) -> str:
        return str(self._get("transliteration", "input_source", default="transcription"))

    @Property(str, notify=settingsChanged)
    def defaultTranslitEngine(self) -> str:
        return str(self._get("transliteration", "engine", default="rule"))

    # ── Slots ─────────────────────────────────────────────────────────────────

    @Slot()
    def loadSettings(self) -> None:
        """Re-fetch settings from the embedded API and notify QML."""
        self._fetch_settings()

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value: Any) -> None:
        """PUT a dot-separated key/value update to the embedded API."""
        try:
            body = QByteArray(json.dumps({"key": key, "value": value}).encode("utf-8"))
            request = QNetworkRequest(QUrl(f"{self._base_url}/settings"))
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            reply = self._net.put(request, body)
            reply.finished.connect(lambda: self._on_setting_saved(reply, key, value))
        except Exception:
            pass

    def _on_setting_saved(self, reply: QNetworkReply, key: str, value: Any) -> None:
        """Apply the server's updated settings snapshot and notify QML."""
        try:
            reply.deleteLater()
            if reply.error() == QNetworkReply.NetworkError.NoError:
                self._settings = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
            self.settingsChanged.emit()
            if key in ("ui.theme", "theme"):
                self.themeChanged.emit(str(value))
        except Exception:
            pass

    @Slot()
    def resetDefaults(self) -> None:
        """Reset all settings to factory defaults via the embedded API."""
        try:
            request = QNetworkRequest(QUrl(f"{self._base_url}/settings/reset"))
            reply = self._net.post(request, QByteArray())
            reply.finished.connect(lambda: self._on_settings_fetched(reply))
        except Exception:
            pass
