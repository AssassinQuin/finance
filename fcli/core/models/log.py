"""Logging and system models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WatchlistAssetDB(BaseModel):
    """Watchlist asset database model."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    code: str = ""  # 用户输入代码
    api_code: str = ""  # API 查询代码
    name: str = ""  # 资产名称
    market: str = ""  # CN, US, HK, GLOBAL
    type: str = ""  # INDEX, FUND, STOCK, BOND, OTHER
    extra: dict[str, Any] = Field(default_factory=dict)  # 扩展信息
    is_active: bool = True
    added_at: datetime | None = None
    updated_at: datetime | None = None
