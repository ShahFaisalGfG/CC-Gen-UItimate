# app.py — CC-Gen-Ultimate GUI entry point

import logging
import os
import sys
from multiprocessing import freeze_support
from typing import Optional

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMessageBox

from ccgen.controllers.app_ctrl import AppController
from ccgen.controllers.assets_ctrl import AssetsController
from ccgen.controllers.prefs_ctrl import PrefsController
from ccgen.controllers.transcription_ctrl import TranscriptionController
from ccgen.ui.boot_thread import BootThread
from ccgen.ui.splash_screen import SplashScreen
from ccgen.utils.helpers import resource_path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
_log = logging.getLogger(__name__)


class _Startup:
    """Owns the splash screen and boot thread, then builds the main window once ready."""

    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._input_paths = [p for p in sys.argv[1:] if os.path.isfile(p)]
        self._engine: Optional[QQmlApplicationEngine] = None
        self._api_server = None
        self._app_ctrl = None
        self._trans_ctrl = None
        self._prefs_ctrl = None
        self._assets_ctrl = None

        self._splash = SplashScreen(resource_path("ccgen/assets/icons/Square310x310Logo.scale-100.png"))
        self._splash.show()

        self._boot = BootThread()
        self._boot.stage_changed.connect(self._splash.set_stage)
        self._boot.boot_ready.connect(self._on_ready)
        self._boot.boot_failed.connect(self._on_failed)
        self._boot.start()

    def _on_ready(self, api_server) -> None:
        """Build controllers and load the QML UI once the backend is ready."""
        try:
            _log.info("Embedded API server ready at %s", api_server.base_url)
            self._api_server = api_server

            icon = QIcon()
            for size in (16, 32, 48, 256):
                path = resource_path(f"ccgen/assets/icons/Square44x44Logo.targetsize-{size}.png")
                if os.path.isfile(path):
                    icon.addFile(path, QSize(size, size))
            if not icon.isNull():
                self._app.setWindowIcon(icon)

            app_ctrl   = AppController()
            trans_ctrl = TranscriptionController(api_server.base_url)
            prefs_ctrl = PrefsController(api_server.base_url)
            assets_ctrl = AssetsController(api_server.base_url)
            if self._input_paths:
                trans_ctrl.addFiles(self._input_paths)
                _log.info("Queued %d file(s) from command line", len(self._input_paths))

            engine = QQmlApplicationEngine()
            ctx = engine.rootContext()
            ctx.setContextProperty("appController",           app_ctrl)
            ctx.setContextProperty("transcriptionController", trans_ctrl)
            ctx.setContextProperty("prefsController",         prefs_ctrl)
            ctx.setContextProperty("modelsController",        assets_ctrl)

            qml_dir = resource_path("ccgen/qml")
            engine.addImportPath(qml_dir)
            engine.load(os.path.join(qml_dir, "main.qml"))

            if not engine.rootObjects():
                self._on_failed("The user interface failed to load.")
                return

            # Kept alive for the app's lifetime - QML's context properties hold
            # only a weak reference, so a garbage-collected controller here
            # would leave bound QML text empty.
            self._engine = engine
            self._app_ctrl = app_ctrl
            self._trans_ctrl = trans_ctrl
            self._prefs_ctrl = prefs_ctrl
            self._assets_ctrl = assets_ctrl
            root = engine.rootObjects()[0]
            self._splash.close()
            if isinstance(root, QQuickWindow):
                root.show()
                _log.info("Window shown — %dx%d at (%d,%d)", root.width(), root.height(), root.x(), root.y())
            else:
                _log.info("Window created (non-QQuickWindow root)")
        except Exception as e:
            _log.critical("Failed to build interface: %r", e, exc_info=True)
            self._on_failed(str(e))

    def _on_failed(self, message: str) -> None:
        """Show a real error dialog and quit instead of hanging silently."""
        _log.critical("Startup failed: %s", message)
        self._splash.set_error(message)
        QMessageBox.critical(None, "CC-Gen-Ultimate", f"Failed to start:\n\n{message}")
        self._splash.close()
        self._app.exit(-1)

    def shutdown(self) -> None:
        """Tear down the QML scene and controllers, then stop the API server."""
        try:
            self._engine = None
            self._app_ctrl = None
            self._trans_ctrl = None
            self._prefs_ctrl = None
            self._assets_ctrl = None
            if self._api_server is not None:
                self._api_server.stop()
        except Exception:
            _log.warning("Error during shutdown", exc_info=True)


def main() -> None:
    """Initialise the Qt application, show the splash, and boot the app in the background."""
    freeze_support()
    _log.info("Starting CC-Gen-Ultimate")

    os.environ.setdefault("QT_QPA_PLATFORM", "windows")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    QQuickStyle.setStyle("Material")
    _log.debug("QML style set to Material")

    app = QApplication(sys.argv)
    # Qt's automatic quit-on-last-window-closed can misfire the instant the
    # splash (a QWidget) closes while a QML window is the only one left open -
    # main.qml's root window quits explicitly on close instead (see main.qml).
    app.setQuitOnLastWindowClosed(False)
    startup = _Startup(app)
    code = app.exec()
    startup.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
