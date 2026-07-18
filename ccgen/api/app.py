# app.py — FastAPI application instance exposing the engines, embedded in the desktop process

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from ccgen.api.routers import jobs, options, settings

_log = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Log startup and shutdown of the embedded API server."""
    _log.info("CC-Gen-Ultimate API starting")
    yield
    _log.info("CC-Gen-Ultimate API stopping")


app = FastAPI(
    title="CC-Gen-Ultimate API",
    lifespan=_lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(settings.router)
app.include_router(options.router)
app.include_router(jobs.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check the desktop app polls before loading the QML UI."""
    return {"status": "ok"}
