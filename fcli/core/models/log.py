"""Logging and system models."""

from typing import Any

from pydantic import BaseModel, Field


class WatchlistAssetDB(BaseModel):
    """Watchlist asset database model."""

    id: int | None = None
    code: str = ""  # 用户输入代码
    api_code: str = ""  # API 查询代码
    name: str = ""  # 资产名称
    market: str = ""  # CN, US, HK, GLOBAL
    type: str = ""  # INDEX, FUND, STOCK, BOND, OTHER
    extra: dict[str, Any] = Field(default_factory=dict)  # 扩展信息
    is_active: bool = True
    added_at: Any | None = None  # datetime
    updated_at: Any | None = None  # datetime

    class Config:
        from_attributes = True
