"""Gold reserve and central bank models."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class GoldReserve(BaseModel):
    """Gold reserve data model for database operations."""

    id: Optional[int] = None
    country_code: str = ""
    country_name: str = ""
    amount_tonnes: float = 0.0
    gold_share_pct: Optional[float] = None  # 占外储比例(%)
    gold_value_usd_m: Optional[float] = None  # 价值(百万美元)
    percent_of_reserves: Optional[float] = None  # deprecated, use gold_share_pct
    report_date: Optional[date] = None
    data_source: str = ""
    fetch_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class CentralBankSchedule(BaseModel):
    """Central bank data release schedule."""

    id: Optional[int] = None
    country_code: str = ""
    country_name: str = ""
    release_day: Optional[int] = None  # Day of month when data is released
    release_frequency: str = "monthly"  # monthly, quarterly
    last_release_date: Optional[date] = None
    next_expected_date: Optional[date] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
