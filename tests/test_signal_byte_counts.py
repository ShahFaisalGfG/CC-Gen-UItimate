# test_signal_byte_counts.py — guards against Qt Signal byte-count overflow
#
# Signal(int) maps to a 32-bit signed C++ int (max ~2.147 GB). Byte counts for
# multi-gigabyte models (e.g. the ~3.1 GB large-v3 Whisper model) exceed that,
# so these progress signals must use the 64-bit 'qlonglong' type instead.

from PySide6.QtCore import QCoreApplication

from ccgen.controllers.assets_ctrl import AssetsController
from ccgen.controllers.transcription_ctrl import TranscriptionController

_OVER_32_BIT = 3_090_835_702  # exceeds 2**31 - 1 (2_147_483_647), e.g. large-v3's size


def _ensure_qt_app() -> None:
    if QCoreApplication.instance() is None:
        QCoreApplication([])


class TestAssetProgressSignal:
    def test_carries_byte_counts_past_32_bit_limit(self):
        _ensure_qt_app()
        controller = AssetsController(base_url="http://127.0.0.1:1")
        received = []
        controller.assetProgress.connect(lambda i, d, t: received.append((i, d, t)))
        controller.assetProgress.emit("whisper:large-v3", _OVER_32_BIT - 100, _OVER_32_BIT)
        assert received == [("whisper:large-v3", _OVER_32_BIT - 100, _OVER_32_BIT)]


class TestTranscriptionProgressSignal:
    def test_carries_byte_counts_past_32_bit_limit(self):
        _ensure_qt_app()
        controller = TranscriptionController(base_url="http://127.0.0.1:1")
        received = []
        controller.progressChanged.connect(lambda d, t: received.append((d, t)))
        controller.progressChanged.emit(_OVER_32_BIT - 100, _OVER_32_BIT)
        assert received == [(_OVER_32_BIT - 100, _OVER_32_BIT)]
