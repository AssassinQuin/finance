import logging
from datetime import datetime
from typing import Any

from ..core.database import Database
from ..core.models.gold_supply_demand import GoldSupplyDemand
from ..core.stores.gold_supply_demand import GoldSupplyDemandStore
from .scrapers.wgc_scraper import WGCScraper

logger = logging.getLogger(__name__)


class GoldSupplyDemandService:
    """Service for gold supply and demand data."""

    def __init__(self):
        self._wgc_scraper = WGCScraper()

    async def fetch_global_supply_demand(self, force_update: bool = False) -> dict | None:
        """Fetch global gold supply/demand data.

        Returns dict with keys: period, year, quarter, supply, demand, price_avg, source.
        """
        if not force_update and Database.is_enabled():
            db_data = await GoldSupplyDemandStore.get_latest()
            if db_data:
                return self._supply_demand_to_dict(db_data)

        data = await self._wgc_scraper.fetch_supply_demand()
        if not data:
            return None

        if Database.is_enabled():
            await self._save_supply_demand_to_db(data)

        return self._format_supply_demand_response(data)

    async def _save_supply_demand_to_db(self, data: Any) -> None:
        """Convert WGC scraper data to GoldSupplyDemand model and save."""
        db_model = GoldSupplyDemand(
            year=data.year,
            quarter=data.quarter,
            period=data.period,
            mine_production=data.supply.mine_production,
            recycling=data.supply.recycling,
            net_hedging=data.supply.net_hedging,
            total_supply=data.supply.total_supply,
            jewelry=data.demand.jewelry,
            technology=data.demand.technology,
            total_investment=data.demand.total_investment,
            bars_coins=data.demand.bars_coins,
            etfs=data.demand.etfs,
            otc_investment=data.demand.otc_investment,
            central_banks=data.demand.central_banks,
            total_demand=data.demand.total_demand,
            supply_demand_balance=data.supply.total_supply - data.demand.total_demand,
            price_avg_usd=data.price_avg,
            data_source="WGC",
            fetch_time=datetime.now(),
        )
        await GoldSupplyDemandStore.save_quarterly(db_model)

    @staticmethod
    def _format_supply_demand_response(data: Any) -> dict:
        """Format WGC scraper data object into response dict."""
        return {
            "period": data.period,
            "year": data.year,
            "quarter": data.quarter,
            "supply": {
                "mine_production": data.supply.mine_production,
                "recycling": data.supply.recycling,
                "net_hedging": data.supply.net_hedging,
                "total": data.supply.total_supply,
            },
            "demand": {
                "jewelry": data.demand.jewelry,
                "technology": data.demand.technology,
                "investment": {
                    "total": data.demand.total_investment,
                    "bars_coins": data.demand.bars_coins,
                    "etfs": data.demand.etfs,
                    "otc": data.demand.otc_investment,
                },
                "central_banks": data.demand.central_banks,
                "total": data.demand.total_demand,
            },
            "price_avg": data.price_avg,
            "source": "WGC",
        }

    @staticmethod
    def _supply_demand_to_dict(db_data: GoldSupplyDemand) -> dict:
        """Convert GoldSupplyDemand DB model to response dict."""
        return {
            "period": db_data.period,
            "year": db_data.year,
            "quarter": db_data.quarter,
            "supply": {
                "mine_production": db_data.mine_production,
                "recycling": db_data.recycling,
                "net_hedging": db_data.net_hedging,
                "total": db_data.total_supply,
            },
            "demand": {
                "jewelry": db_data.jewelry,
                "technology": db_data.technology,
                "investment": {
                    "total": db_data.total_investment,
                    "bars_coins": db_data.bars_coins,
                    "etfs": db_data.etfs,
                    "otc": db_data.otc_investment,
                },
                "central_banks": db_data.central_banks,
                "total": db_data.total_demand,
            },
            "price_avg": db_data.price_avg_usd,
            "source": db_data.data_source or "WGC",
        }

    async def get_supply_demand_history(self, limit: int = 8) -> list[dict]:
        """Get historical supply/demand data from database."""
        records = await GoldSupplyDemandStore.get_history(limit)
        return [self._supply_demand_to_dict(r) for r in records]

    async def get_supply_demand_by_quarter(self, year: int, quarter: int) -> dict | None:
        """Get supply/demand data for a specific quarter."""
        data = await GoldSupplyDemandStore.get_by_quarter(year, quarter)
        if data:
            return self._supply_demand_to_dict(data)
        return None


gold_supply_demand_service = GoldSupplyDemandService()
