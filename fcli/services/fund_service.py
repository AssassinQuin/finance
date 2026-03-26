"""Fund service for data management."""

import logging
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

from ..core.database import Database
from ..core.models import Fund, FundType
from ..core.stores import FundStore
from .scrapers.fund_scraper import FundScraper

logger = logging.getLogger(__name__)


class FundService:
    """Service for fund data operations."""

    def __init__(self):
        self.scraper = FundScraper()

    async def needs_monthly_update(self) -> bool:
        """Check if monthly update is needed."""
        if not Database.is_enabled():
            return False

        try:
            row = await Database.fetch_one(
                "SELECT MAX(updated_at) as last_update FROM dim_fund"
            )
            if not row or not row.get("last_update"):
                return True

            last_update = row["last_update"]
            now = datetime.now(timezone.utc)

            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=timezone.utc)

            threshold = now - relativedelta(months=1)
            return last_update < threshold
        except Exception as e:
            logger.error(f"Failed to check update status: {e}")
            return True

    async def update_fund_data(self, fund_type: str | None = None, force: bool = False) -> int:
        """Update fund data from AKShare."""
        if not force and not await self.needs_monthly_update():
            logger.info("Fund data is up to date (monthly check)")
            return 0

        type_enum = None
        if fund_type:
            type_enum = FundType(fund_type.upper())

        result = await self.scraper.scrape_funds(type_enum)

        if not result.success:
            logger.error(f"Failed to scrape fund data: {result.error_message}")
            return 0

        funds = result.data
        if not funds:
            logger.warning("No funds scraped")
            return 0

        saved_count = await FundStore.save_batch(funds)
        logger.info(f"Saved {saved_count} funds to database")

        return saved_count

    async def update_us_indices(self, force: bool = False) -> int:
        """Update US market indices and ETFs."""
        if not force and not await self.needs_monthly_update():
            logger.info("US fund data is up to date (monthly check)")
            return 0

        funds = await self.scraper.scrape_us_indices()

        if not funds:
            logger.warning("No US indices scraped")
            return 0

        saved_count = await FundStore.save_batch(funds)
        logger.info(f"Saved {saved_count} US indices to database")

        return saved_count


fund_service = FundService()
