# api_client.py - asynchronous JSON calls from the Qt controllers to the embedded API

import json
import logging
from typing import Any, Callable, Optional

from PySide6.QtCore import QByteArray, QObject, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWebSockets import QWebSocket

_log = logging.getLogger(__name__)

# Called with (parsed JSON body or None, error message or "").
ReplyHandler = Callable[[Any, str], None]


class ApiClient(QObject):
    """Sends JSON requests on the GUI thread's event loop and parses replies for a callback."""

    def __init__(self, base_url: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._base_url = base_url.rstrip("/")
        self._net = QNetworkAccessManager(self)

    def get(self, path: str, handler: Optional[ReplyHandler] = None) -> None:
        """GET `path` and pass the parsed body to handler."""
        self._watch(self._net.get(self._request(path)), handler)

    def post(self, path: str, body: Any = None, handler: Optional[ReplyHandler] = None) -> None:
        """POST an optional JSON body to `path`."""
        self._watch(self._net.post(self._request(path), self._encode(body)), handler)

    def put(self, path: str, body: Any, handler: Optional[ReplyHandler] = None) -> None:
        """PUT a JSON body to `path`."""
        self._watch(self._net.put(self._request(path), self._encode(body)), handler)

    def patch(self, path: str, body: Any, handler: Optional[ReplyHandler] = None) -> None:
        """PATCH a JSON body to `path`."""
        reply = self._net.sendCustomRequest(self._request(path), QByteArray(b"PATCH"), self._encode(body))
        self._watch(reply, handler)

    def delete(self, path: str, handler: Optional[ReplyHandler] = None) -> None:
        """DELETE `path`."""
        self._watch(self._net.deleteResource(self._request(path)), handler)

    def open_stream(self, path: str, on_message: Callable[[dict[str, Any]], None]) -> QWebSocket:
        """Open a WebSocket to `path` and deliver each JSON message to on_message."""
        socket = QWebSocket(parent=self)

        def dispatch(text: str) -> None:
            try:
                on_message(json.loads(text))
            except Exception:
                _log.error("Bad stream message from %s", path, exc_info=True)

        socket.textMessageReceived.connect(dispatch)
        ws_base = self._base_url.replace("http://", "ws://").replace("https://", "wss://")
        socket.open(QUrl(f"{ws_base}{path}"))
        return socket

    def _request(self, path: str) -> QNetworkRequest:
        """Build a JSON request for an API path."""
        request = QNetworkRequest(QUrl(f"{self._base_url}{path}"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        return request

    @staticmethod
    def _encode(body: Any) -> QByteArray:
        """Serialize a request body (None sends an empty body)."""
        return QByteArray(b"" if body is None else json.dumps(body).encode("utf-8"))

    @staticmethod
    def _watch(reply: QNetworkReply, handler: Optional[ReplyHandler]) -> None:
        """Parse the reply when it finishes and hand the result to handler."""

        def finished() -> None:
            reply.deleteLater()
            data: Any = None
            error = ""
            raw = bytes(reply.readAll().data())
            if raw:
                try:
                    data = json.loads(raw.decode("utf-8"))
                except ValueError:
                    error = "The local service returned an unreadable response."
            if reply.error() != QNetworkReply.NetworkError.NoError:
                detail = data.get("detail") if isinstance(data, dict) else None
                error = str(detail or reply.errorString())
                _log.warning("API %s failed: %s", reply.url().path(), error)
            if handler is not None:
                try:
                    handler(data if not error else None, error)
                except Exception:
                    _log.error("API reply handler failed", exc_info=True)

        reply.finished.connect(finished)
