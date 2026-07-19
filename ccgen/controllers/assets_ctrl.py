# assets_ctrl.py — Manage Models controller (HTTP/WebSocket client of the embedded API)

import json
from typing import Any

from PySide6.QtCore import Property, QByteArray, QObject, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWebSockets import QWebSocket


class AssetsController(QObject):
    """Lists and manages downloadable models/engines/languages via the embedded API."""

    assetsChanged   = Signal()
    assetQueued     = Signal(str)
    # 64-bit: byte counts for multi-gigabyte models (e.g. large-v3, ~3.1 GB) overflow a
    # plain 32-bit Qt `int` (max ~2.147 GB), which raised inside PySide6's binding layer
    # and was silently swallowed by _on_stream_message's broad except - dropping every
    # progress event for any asset whose size crosses that line.
    assetProgress   = Signal(str, 'qlonglong', 'qlonglong')  # type: ignore[arg-type]
    assetStatus     = Signal(str, str)
    assetFinished   = Signal(str, bool, str)

    def __init__(self, base_url: str, parent=None):
        super().__init__(parent)
        self._base_url = base_url
        self._net = QNetworkAccessManager(self)
        self._assets: list[dict[str, Any]] = []
        self._socket = QWebSocket()
        self._socket.textMessageReceived.connect(self._on_stream_message)
        self._socket.open(QUrl(f"{self._ws_base_url()}/assets/stream"))
        self.refreshAssets()

    def _ws_base_url(self) -> str:
        """Return the base URL rewritten to the ws(s):// scheme."""
        return self._base_url.replace("http://", "ws://").replace("https://", "wss://")

    @Property("QVariantList", notify=assetsChanged)  # type: ignore[arg-type]
    def assets(self) -> list:
        """Current catalog snapshot: id/category/label/downloaded/size for every asset."""
        return self._assets

    @Slot()
    def refreshAssets(self) -> None:
        """Re-fetch the asset catalog from the embedded API."""
        request = QNetworkRequest(QUrl(f"{self._base_url}/assets"))
        reply = self._net.get(request)
        reply.finished.connect(lambda: self._on_assets_fetched(reply))

    def _on_assets_fetched(self, reply: QNetworkReply) -> None:
        """Apply the fetched catalog and notify QML."""
        try:
            reply.deleteLater()
            if reply.error() != QNetworkReply.NetworkError.NoError:
                return
            self._assets = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
            self.assetsChanged.emit()
        except Exception:
            pass

    @Slot(str)
    def downloadAsset(self, asset_id: str) -> None:
        """Queue an asset for download."""
        request = QNetworkRequest(QUrl(f"{self._base_url}/assets/{asset_id}/download"))
        reply = self._net.post(request, QByteArray())
        reply.finished.connect(reply.deleteLater)

    @Slot(str)
    def cancelAsset(self, asset_id: str) -> None:
        """Cancel a queued or in-progress asset download."""
        request = QNetworkRequest(QUrl(f"{self._base_url}/assets/{asset_id}/cancel"))
        reply = self._net.post(request, QByteArray())
        reply.finished.connect(reply.deleteLater)

    @Slot(str)
    def removeAsset(self, asset_id: str) -> None:
        """Delete a downloaded asset from local storage."""
        request = QNetworkRequest(QUrl(f"{self._base_url}/assets/{asset_id}"))
        reply = self._net.deleteResource(request)
        reply.finished.connect(lambda: self._on_asset_removed(reply))

    def _on_asset_removed(self, reply: QNetworkReply) -> None:
        """Refresh the catalog once a removal request completes."""
        reply.deleteLater()
        self.refreshAssets()

    def _on_stream_message(self, message: str) -> None:
        """Parse one JSON event from the assets stream and re-emit the matching Qt signal."""
        try:
            event: dict[str, Any] = json.loads(message)
            kind = event.get("event")
            if kind == "queued":
                self.assetQueued.emit(event["id"])
            elif kind == "status":
                self.assetStatus.emit(event["id"], event["message"])
            elif kind == "progress":
                self.assetProgress.emit(event["id"], event["done"], event["total"])
            elif kind == "finished":
                self.assetFinished.emit(
                    event["id"], bool(event.get("success")), event.get("error") or ""
                )
                self.refreshAssets()
        except Exception:
            pass
