"""Logging and system models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .base import AssetType, Market


class WatchlistAssetDB(BaseModel):
    """Watchlist asset database model."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    code: str = ""
    api_code: str = ""
    name: str = ""
    market: Market = Market.CN
    type: AssetType = AssetType.STOCK
    extra: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    added_at: datetime | None = None
    updated_at: datetime | None = None
