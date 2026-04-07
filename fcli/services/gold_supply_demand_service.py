from ..core.database import Database
from ..core.stores.gold_supply_demand import gold_supply_demand_store
from ..utils.logger import get_logger
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

        records = await self._wgc_scraper.fetch_latest()
        if not records:
            return None

        # DB table enforces quarter in 1..4; ignore annual rows (quarter=0).
        quarterly_records = [r for r in records if r.quarter and 1 <= r.quarter <= 4]
        display_candidates = quarterly_records or records

        if Database.is_enabled():
            for record in quarterly_records:
                await gold_supply_demand_store.save_quarterly(record)

        latest = max(display_candidates, key=lambda r: (r.year, r.quarter))
        return latest.to_display_dict()

    async def get_supply_demand_history(self, limit: int = 8) -> list[dict]:
        records = await gold_supply_demand_store.get_history(limit)
        return [r.to_display_dict() for r in records]

    async def get_supply_demand_by_quarter(self, year: int, quarter: int) -> dict | None:
        data = await gold_supply_demand_store.get_by_quarter(year, quarter)
        if data:
            return data.to_display_dict()
        return None
