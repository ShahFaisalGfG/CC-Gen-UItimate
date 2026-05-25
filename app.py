# app.py — CC-Gen-Ultimate GUI entry point

import logging
import os
import sys
from multiprocessing import freeze_support

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from ccgen.controllers.app_ctrl import AppController
from ccgen.controllers.prefs_ctrl import PrefsController
from ccgen.controllers.transcription_ctrl import TranscriptionController
from ccgen.utils.helpers import resource_path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
_log = logging.getLogger(__name__)


def main() -> None:
    """Initialise the Qt application and launch the QML engine."""
    freeze_support()
    _log.info("Starting CC-Gen-Ultimate")

    os.environ.setdefault("QT_QPA_PLATFORM", "windows")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    QQuickStyle.setStyle("Material")
    _log.debug("QML style set to Material")

    app = QApplication(sys.argv)

    icon = QIcon()
    for _sz in [16, 32, 48, 256]:
        _p = resource_path(f"ccgen/assets/icons/Square44x44Logo.targetsize-{_sz}.png")
        if os.path.isfile(_p):
            icon.addFile(_p, QSize(_sz, _sz))
    if not icon.isNull():
        app.setWindowIcon(icon)

    app_ctrl   = AppController()
    trans_ctrl = TranscriptionController()
    prefs_ctrl = PrefsController()
    _log.debug("Controllers ready")

    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("appController",           app_ctrl)
    ctx.setContextProperty("transcriptionController", trans_ctrl)
    ctx.setContextProperty("prefsController",         prefs_ctrl)

    qml_dir = resource_path("ccgen/qml")
    engine.addImportPath(qml_dir)

    main_qml = os.path.join(qml_dir, "main.qml")
    _log.info("Loading QML: %s", main_qml)
    engine.load(main_qml)

    if not engine.rootObjects():
        _log.critical("QML failed to load — no root objects")
        sys.exit(-1)

    root = engine.rootObjects()[0]
    if isinstance(root, QQuickWindow):
        root.show()
        _log.info("Window shown — %dx%d at (%d,%d)", root.width(), root.height(), root.x(), root.y())
    else:
        _log.info("Window created (non-QQuickWindow root)")
    code = app.exec()
    del engine          # destroy QML scene before Python controllers are GC'd
    sys.exit(code)


if __name__ == "__main__":
    main()
