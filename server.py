# server.py — standalone dev entry point for the FastAPI backend
#
# The packaged desktop app does not use this file; app.py boots the same FastAPI app
# in-thread via ccgen.api.embedded. This is only for running/testing the API on its own,
# e.g. `python server.py` then `curl http://127.0.0.1:8756/health`.

import uvicorn

from ccgen.api.embedded import DEFAULT_HOST, DEFAULT_PORT


def main() -> None:
    """Run the API server standalone, with auto-reload for development."""
    uvicorn.run("ccgen.api.app:app", host=DEFAULT_HOST, port=DEFAULT_PORT, reload=True)


if __name__ == "__main__":
    main()
