# app_ctrl.py — main window controller (theme, logs, app info)

import subprocess
import sys
import winreg

from PySide6.QtCore import Property, QObject, Signal, Slot

from ccgen.config.defaults import AppInfo
from ccgen.utils.settings import load_settings, save_settings


def _detect_system_theme() -> str:
    """Read Windows registry to determine the current light or dark mode."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value == 1 else "dark"
    except Exception:
        return "light"


class AppController(QObject):
    """Exposes main-window state (theme, logs, app metadata) to QML."""

    themeChanged = Signal(str)
    logAppended  = Signal(str)
    logsCleared  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logs: list[str] = []
        settings = load_settings()
        raw = settings.get("ui", {}).get("theme", "system")
        self._theme = _detect_system_theme() if raw == "system" else raw

    # ── Properties ───────────────────────────────────────────────────────────

    @Property(str, notify=themeChanged)
    def currentTheme(self) -> str:
        """Resolved theme name: 'light' or 'dark'."""
        return self._theme

    @Property(str, constant=True)
    def appName(self) -> str:
        """Application display name."""
        return AppInfo.APP_NAME

    @Property(str, constant=True)
    def appVersion(self) -> str:
        """Application version string."""
        return AppInfo.APP_VERSION

    @Property(str, constant=True)
    def appDescription(self) -> str:
        """Short application description."""
        return AppInfo.APP_DESCRIPTION

    @Property(str, constant=True)
    def appAuthor(self) -> str:
        """Application author."""
        return AppInfo.APP_AUTHOR

    # ── Slots ────────────────────────────────────────────────────────────────

    @Slot()
    def detectTheme(self) -> None:
        """Re-detect system theme and emit themeChanged if it changed."""
        try:
            settings = load_settings()
            raw = settings.get("ui", {}).get("theme", "system")
            new_theme = _detect_system_theme() if raw == "system" else raw
            if new_theme != self._theme:
                self._theme = new_theme
                self.themeChanged.emit(self._theme)
        except Exception:
            pass

    @Slot(str)
    def applyTheme(self, theme: str) -> None:
        """Apply and persist a theme choice ('system', 'light', 'dark')."""
        try:
            resolved = _detect_system_theme() if theme == "system" else theme
            if resolved != self._theme:
                self._theme = resolved
                self.themeChanged.emit(self._theme)
            settings = load_settings()
            settings.setdefault("ui", {})["theme"] = theme
            save_settings(settings)
        except Exception:
            pass

    @Slot(str)
    def appendLog(self, message: str) -> None:
        """Add a message to the in-memory log and notify QML."""
        try:
            self._logs.append(message)
            self.logAppended.emit(message)
        except Exception:
            pass

    @Slot()
    def clearLogs(self) -> None:
        """Clear all in-memory log entries and notify QML."""
        try:
            self._logs.clear()
            self.logsCleared.emit()
        except Exception:
            pass

    @Slot(result=str)
    def logsText(self) -> str:
        """Return all log entries joined by newlines."""
        try:
            return "\n".join(self._logs)
        except Exception:
            return ""

    @Slot()
    def openOutputFolder(self, path: str) -> None:
        """Open the folder containing a file in Windows Explorer."""
        try:
            import os
            folder = os.path.dirname(path)
            if sys.platform == "win32":
                subprocess.run(["explorer", folder], check=False)
        except Exception:
            pass
