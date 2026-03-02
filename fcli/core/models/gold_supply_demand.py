"""Gold supply and demand quarterly data model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GoldSupplyDemand(BaseModel):
    """Gold supply/demand data model for quarterly storage."""

    id: Optional[int] = None
    year: int
    quarter: int  # 1-4
    period: str = ""  # e.g. "2024 Q1"

    # Supply side (tonnes)
    mine_production: float = 0.0
    recycling: float = 0.0
    net_hedging: float = 0.0
    total_supply: float = 0.0

    # Demand side (tonnes)
    jewelry: float = 0.0
    technology: float = 0.0
    total_investment: float = 0.0
    bars_coins: float = 0.0
    etfs: float = 0.0
    otc_investment: float = 0.0
    central_banks: float = 0.0
    total_demand: float = 0.0

    # Balance and price
    supply_demand_balance: float = 0.0  # total_supply - total_demand
    price_avg_usd: Optional[float] = None  # Average gold price in USD/oz

    # Metadata
    data_source: str = ""
    fetch_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
