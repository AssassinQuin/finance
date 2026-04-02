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

    def to_display_dict(self) -> dict:
        return {
            "period": self.period,
            "year": self.year,
            "quarter": self.quarter,
            "supply": {
                "mine_production": self.mine_production,
                "recycling": self.recycling,
                "net_hedging": self.net_hedging,
                "total": self.total_supply,
            },
            "demand": {
                "jewelry": self.jewelry,
                "technology": self.technology,
                "investment": {
                    "total": self.total_investment,
                    "bars_coins": self.bars_coins,
                    "etfs": self.etfs,
                    "otc": self.otc_investment,
                },
                "central_banks": self.central_banks,
                "total": self.total_demand,
            },
            "price_avg": self.price_avg_usd,
            "source": self.data_source or "WGC",
        }
