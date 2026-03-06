"""Asset and Quote models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .base import AssetType, Market


class Asset(BaseModel):
    """User's watchlist asset."""

    code: str = Field(..., description="User facing code, e.g., SP500, 000218")
    api_code: str = Field(..., description="API parameter, e.g., gb_$spx")
    name: str
    market: Market
    type: AssetType
    added_at: datetime = Field(default_factory=datetime.now)
    extra: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Quote(BaseModel):
    """Real-time quote data."""

    code: str
    name: str
    price: float
    change_percent: float
    update_time: datetime  # 使用 datetime 类型，在展示层格式化
    market: Market
    type: AssetType
    currency: str | None = None
    high: float | None = None
    low: float | None = None
    volume: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ExchangeRate(BaseModel):
    """Exchange rate data."""

    base_currency: str = Field(..., description="Base currency code, e.g., USD")
    quote_currency: str = Field(..., description="Quote currency code, e.g., CNY")
    rate: float = Field(..., description="Exchange rate")
    source: str | None = Field(None, description="Data source")
    update_time: datetime | None = Field(None, description="Last update time")
