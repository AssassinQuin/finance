"""Logging and system models."""

from datetime import datetime
from typing import Optional, Any, Dict

from pydantic import BaseModel, Field


class FetchLog(BaseModel):
    """Fetch operation log."""
    id: Optional[int] = None
    data_type: str = ""  # gold_reserves, etc.
    source: str = ""  # WGC, IMF, etc.
    status: str = ""  # success, failed, partial
    records_count: int = 0
    duration_ms: int = 0
    error_message: Optional[str] = None
    timestamp: Optional[Any] = None  # datetime

    class Config:
        from_attributes = True


class WatchlistAssetDB(BaseModel):
    """Watchlist asset database model."""
    id: Optional[int] = None
    code: str = ""  # 用户输入代码
    api_code: str = ""  # API 查询代码
    name: str = ""  # 资产名称
    market: str = ""  # CN, US, HK, GLOBAL
    type: str = ""  # INDEX, FUND, STOCK, BOND, OTHER
    extra: Dict[str, Any] = Field(default_factory=dict)  # 扩展信息
    is_active: bool = True
    added_at: Optional[Any] = None  # datetime
    updated_at: Optional[Any] = None  # datetime

    class Config:
        from_attributes = True
