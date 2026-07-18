# embedded.py — runs the FastAPI app on a background thread inside the desktop process

import logging
import threading
import time
from typing import Optional

import uvicorn

from ccgen.api.app import app

_log = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8756  # used only by server.py's standalone dev entry point, for a predictable URL
AUTO_PORT = 0  # ask the OS for any free ephemeral port - what EmbeddedServer uses by default


class EmbeddedServer:
    """Runs the FastAPI app on a daemon thread for the desktop app's lifetime.

    Binds an OS-assigned free port by default (port=0) rather than a fixed one, so the app can
    never collide with another local service - including other dev tools on the same machine.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = AUTO_PORT) -> None:
        self._host = host
        self._port = port
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start uvicorn on a daemon thread. Does not block the caller.

        log_config=None keeps uvicorn from installing its own logging formatters, which probe
        sys.stderr.isatty() - that call crashes when sys.stderr is None, as it is in a frozen
        --windowed build with no console attached. The app's own logging.basicConfig() already
        covers this logger.
        """
        config = uvicorn.Config(
            app, host=self._host, port=self._port, log_level="warning", log_config=None,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True, name="ccgen-api")
        self._thread.start()
        _log.info("Embedded API server starting on %s (port requested: %s)", self._host, self._port or "auto")

    def wait_ready(self, timeout: float = 10.0) -> bool:
        """Block until the server reports it has started serving, or timeout elapses."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._server is not None and self._server.started:
                self._resolve_bound_port()
                return True
            time.sleep(0.05)
        return False

    def _resolve_bound_port(self) -> None:
        """Read back the actual bound port from the running server (needed when port=0)."""
        try:
            if self._server is not None and self._server.servers:
                sockets = self._server.servers[0].sockets
                if sockets:
                    self._port = sockets[0].getsockname()[1]
        except Exception:
            _log.warning("Could not resolve the embedded server's bound port", exc_info=True)

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
