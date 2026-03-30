"""Gold supply and demand quarterly data model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GoldSupplyDemand(BaseModel):
    """Gold supply/demand data model matching wide fact table."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    year: int
    quarter: int
    period: str = ""

    mine_production: float | None = None
    recycling: float | None = None
    net_hedging: float | None = None
    total_supply: float | None = None
    jewelry: float | None = None
    technology: float | None = None
    total_investment: float | None = None
    bars_coins: float | None = None
    etfs: float | None = None
    otc_investment: float | None = None
    central_banks: float | None = None
    total_demand: float | None = None
    supply_demand_balance: float | None = None
    price_avg_usd: float | None = None

    data_source: str = "WGC"
    fetch_time: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
