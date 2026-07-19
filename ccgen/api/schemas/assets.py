# assets.py — response contract for the Manage Models catalog

from typing import Optional

from pydantic import BaseModel


class AssetOut(BaseModel):
    """One row in the Manage Models catalog, returned to the QML client."""

    id: str
    category: str
    engine: str
    label: str
    downloaded: bool
    size_bytes: Optional[int] = None
    approx_size_mb: Optional[int] = None
