from typing import Any

from ..core.database import Database
from ..core.models.gold_supply_demand import GoldSupplyDemand
from ..core.stores.gold_supply_demand import gold_supply_demand_store
from ..utils.logger import get_logger
from ..utils.time_util import utcnow
from .scrapers.wgc_scraper import WGCScraper

logger = get_logger("fcli.gold_supply_demand")


class GoldSupplyDemandService:
    """Service for gold supply and demand data."""

    def __init__(self, wgc_scraper: WGCScraper):
        self._wgc_scraper = wgc_scraper

    async def fetch_global_supply_demand(self, force_update: bool = False) -> dict | None:
        if not force_update and Database.is_enabled():
            db_data = await gold_supply_demand_store.get_latest()
            if db_data:
                return db_data.to_display_dict()

        data = await self._wgc_scraper.fetch_latest()
        if not data:
            return None

        if Database.is_enabled():
            await self._save_supply_demand_to_db(data)

        return self._scraper_data_to_model(data).to_display_dict()

    @staticmethod
    def _scraper_data_to_model(data: Any) -> GoldSupplyDemand:
        return GoldSupplyDemand(
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
            fetch_time=utcnow(),
        )

    async def _save_supply_demand_to_db(self, data: Any) -> None:
        db_model = self._scraper_data_to_model(data)
        await gold_supply_demand_store.save_quarterly(db_model)

    async def get_supply_demand_history(self, limit: int = 8) -> list[dict]:
        records = await gold_supply_demand_store.get_history(limit)
        return [r.to_display_dict() for r in records]

    async def get_supply_demand_by_quarter(self, year: int, quarter: int) -> dict | None:
        data = await gold_supply_demand_store.get_by_quarter(year, quarter)
        if data:
            return data.to_display_dict()
        return None
