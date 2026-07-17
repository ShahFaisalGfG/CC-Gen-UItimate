# embedded.py — runs the FastAPI app on a background thread inside the desktop process

import logging
import threading
import time
from typing import Optional

import uvicorn

from ccgen.api.app import app

_log = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8756


class EmbeddedServer:
    """Runs the FastAPI app on a daemon thread for the desktop app's lifetime."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self._host = host
        self._port = port
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start uvicorn on a daemon thread. Does not block the caller."""
        config = uvicorn.Config(app, host=self._host, port=self._port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True, name="ccgen-api")
        self._thread.start()
        _log.info("Embedded API server starting on %s", self.base_url)

    def wait_ready(self, timeout: float = 10.0) -> bool:
        """Block until the server reports it has started serving, or timeout elapses."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._server is not None and self._server.started:
                return True
            time.sleep(0.05)
        return False

    def stop(self) -> None:
        """Signal uvicorn to shut down."""
        try:
            if self._server is not None:
                self._server.should_exit = True
        except Exception:
            _log.warning("Failed to signal embedded API server shutdown", exc_info=True)

    @property
    def base_url(self) -> str:
        """Base HTTP URL of the embedded server."""
        return f"http://{self._host}:{self._port}"
