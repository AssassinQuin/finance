"""Fund service for data management."""

from dateutil.relativedelta import relativedelta

from ..core.database import Database
from ..core.models import Fund, FundDetail, FundType
from ..core.stores.fund import fund_store
from ..utils.logger import get_logger
from ..utils.time_util import utcnow
from .scrapers.fund_scraper import FundScraper

logger = get_logger("fcli.fund")


class FundService:
    """Service for fund data operations."""

    def __init__(self, fund_scraper: FundScraper | None = None):
        self.scraper = fund_scraper or FundScraper()

    async def needs_monthly_update(self) -> bool:
        if not Database.is_enabled():
            return False

        try:
            row = await Database.fetch_one("SELECT MAX(updated_at) as last_update FROM funds")
            if not row or not row.get("last_update"):
                return True

            last_update = row["last_update"]
            now = utcnow()

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

        saved_count = await fund_store.save_batch(funds)
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

        saved_count = await fund_store.save_batch(funds)
        logger.info(f"Saved {saved_count} US indices to database")

        return saved_count

    async def search(self, query: str, fund_type: FundType | None = None, limit: int = 20) -> list[Fund]:
        return await fund_store.search(query, fund_type, limit)

    async def get_detail(self, code: str) -> FundDetail | None:
        fund = await fund_store.get_by_code(code)
        if not fund:
            return None
        scale_history = await fund_store.get_scale_history(code)
        return FundDetail.from_fund(fund, scale_history)
