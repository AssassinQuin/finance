"""Gold reserve data service.

Provides gold reserve data access with database-first strategy
and IMF API fallback.
"""

from datetime import date, datetime
from typing import Any

from dateutil.relativedelta import relativedelta

from ..core.database import Database
from ..core.models.gold import GoldReserve
from ..core.stores.gold import gold_reserve_store
from ..utils.logger import get_logger
from ..utils.time_util import utcnow
from .scrapers.imf_scraper import IMFScraper

logger = get_logger("fcli.gold_reserve")


class GoldReserveService:
    """Service for accessing gold reserve data."""

    def __init__(self, imf_scraper: IMFScraper):
        self._imf_scraper = imf_scraper

    async def fetch_all_with_auto_update(self, force: bool = False) -> list[dict]:
        """Fetch latest gold reserves with auto-update.

        Main entry point used by CLI commands. Returns presenter-format dicts.

        Args:
            force: If True, refresh data from IMF before fetching.

        Returns:
            List of dicts with keys: country, code, amount, date, source,
            yoy_change, ytd_change, monthly_trend, trend_r2.
        """
        if force:
            await self.save_to_database(years=1)
        else:
            await self._check_and_update_stale_data()

        if Database.is_enabled():
            try:
                results = await gold_reserve_store.get_latest_with_stats(
                    min_date=(date.today() + relativedelta(months=-6)).replace(day=1)
                )
                if results:
                    return self._format_stats_results(results)
            except Exception as e:
                logger.warning("DB query failed, falling back to IMF API: %s", e)

        # Fallback to IMF API
        try:
            reserves = await self._imf_scraper.batch_get_latest_reserves()
            return [
                self._transform_imf_to_dict(
                    country_name=r.country_name,
                    country_code=r.country_code,
                    amount=r.amount_tonnes,
                    period=r.report_date,
                    source=r.data_source or "IMF",
                )
                for r in reserves
            ]
        except Exception as e:
            logger.error("IMF API fallback also failed: %s", e)
            return []

    async def _check_and_update_stale_data(self, country_codes=None):
        """Check for stale data and trigger update for outdated countries."""
        if not Database.is_enabled():
            return

        try:
            target_date = date.today().replace(day=1) - relativedelta(months=1)

            latest_dates = await gold_reserve_store.get_all_latest_dates()
            if not latest_dates:
                # No data at all, do full refresh
                await self.save_to_database(years=1)
                return

            stale_codes = [code for code, latest in latest_dates.items() if latest < target_date]

            if country_codes:
                stale_codes = [code for code in stale_codes if code in country_codes]

            if stale_codes:
                logger.info(
                    "Auto-updating %d countries with stale data...",
                    len(stale_codes),
                )
                await self.save_to_database(country_codes=stale_codes, years=1)
                return

            if not country_codes:
                await self.save_to_database(years=1)
        except Exception as e:
            logger.warning("Stale data check failed: %s", e)

    async def save_to_database(self, country_codes=None, years: int = 10) -> int:
        """Fetch gold reserve history from IMF and save to database.

        Args:
            country_codes: Optional list of country codes to fetch.
                If None, fetches all supported countries.
            years: Number of years of history to fetch.

        Returns:
            Number of records saved.
        """
        try:
            # batch_get_history_dict returns list[dict] with keys:
            # country_code, country_name, data (dict of period→tonnes)
            history = await self._imf_scraper.batch_get_history_dict(country_codes, years=years)

            if not history:
                logger.warning("No history data returned from IMF scraper")
                return 0

            reserves: list[GoldReserve] = []
            fetch_time = utcnow()

            for country_data in history:
                code = country_data.get("country_code", "")
                name = country_data.get("country_name", code)
                for period, tonnes in country_data.get("data", {}).items():
                    if tonnes is None:
                        continue
                    try:
                        report_date = datetime.strptime(period, "%Y-%m").date()
                    except ValueError:
                        continue
                    reserves.append(
                        GoldReserve(
                            country_code=code,
                            country_name=name,
                            amount_tonnes=float(tonnes),
                            report_date=report_date,
                            data_source="IMF",
                            fetch_time=fetch_time,
                        )
                    )

            if not reserves:
                return 0

            total_saved = await gold_reserve_store.save_batch(reserves)
            logger.info("Saved %d gold reserve records", total_saved)
            return total_saved

        except Exception as e:
            logger.error("Failed to save gold reserves to database: %s", e)
            return 0

    async def get_history(self, country_code: str, months: int = 120) -> list[dict]:
        """Get historical gold reserves for a country.

        Args:
            country_code: ISO country code (e.g. 'CHN').
            months: Number of months of history.

        Returns:
            List of dicts with date and amount.
        """
        if Database.is_enabled():
            try:
                days = months * 30
                records = await gold_reserve_store.get_country_history(country_code, days)
                if records:
                    return [
                        {
                            "date": r.report_date,
                            "amount": r.amount_tonnes,
                        }
                        for r in records
                    ]
            except Exception as e:
                logger.warning("DB history query failed, falling back to IMF: %s", e)

        # IMF fallback
        years = max(1, months // 12)
        result = await self._imf_scraper.get_gold_reserves_history_dict(country_code, years=years)
        if isinstance(result, dict):
            return [
                {"date": period, "amount": tonnes} for period, tonnes in sorted(result.items()) if tonnes is not None
            ]
        return result if isinstance(result, list) else []

    async def get_all_history(self, years: int = 10) -> dict[str, list[dict]]:
        """Get historical gold reserves for all countries.

        Args:
            years: Number of years of history.

        Returns:
            Dict mapping country codes to lists of {date, amount} dicts.
        """
        return await self._imf_scraper.batch_get_history_dict(years=years)

    async def get_china_history_online(self, months: int = 60) -> list[dict]:
        """Get China gold reserve history from online source.

        Args:
            months: Number of months of history.

        Returns:
            List of dicts with 'date' and 'amount' keys.
        """
        records = await self.get_history("CHN", months)
        return [{"date": r["date"], "amount": r["amount"]} for r in records]

    async def get_top_trend_data(self, top_n: int = 5, months: int = 36) -> dict[str, list[dict]]:
        """Get historical trend data for top N gold-holding countries.

        Args:
            top_n: Number of top countries.
            months: Number of months of history.

        Returns:
            Dict mapping country names to lists of {date, amount} dicts.
        """
        if not Database.is_enabled():
            return {}

        return await gold_reserve_store.get_top_countries_history(top_n, months)

    def get_supported_countries(self) -> dict[str, str]:
        """Return dict of supported country codes to names.

        Returns:
            Dict mapping country codes to country names.
        """
        return IMFScraper.GOLD_COUNTRY_CODES

    def _transform_imf_to_dict(
        self,
        country_name: str,
        country_code: str,
        amount: Any,
        period: Any,
        source: str = "IMF",
    ) -> dict:
        """Transform IMF scraper fields to presenter format.

        Args:
            country_name: Full country name.
            country_code: ISO country code.
            amount: Gold reserve in tonnes.
            period: Reporting period.
            source: Data source name.

        Returns:
            Dict with presenter-compatible keys.
        """
        return {
            "country": country_name,
            "code": country_code,
            "amount": amount,
            "date": period,
            "source": source,
        }

    @staticmethod
    def _format_stats_results(results: list[dict]) -> list[dict]:
        """Map store column names to presenter field names.

        Args:
            results: List of dicts from GoldReserveStore.get_latest_with_stats().

        Returns:
            List of dicts with presenter-compatible keys.
        """
        formatted = []
        for row in results:
            report_date = row.get("report_date")
            if isinstance(report_date, date | datetime):
                date_str = report_date.strftime("%Y-%m")
            else:
                date_str = str(report_date) if report_date else ""

            formatted.append(
                {
                    "country": row.get("country_name", ""),
                    "code": row.get("country_code", ""),
                    "amount": float(row.get("gold_tonnes", 0)),
                    "date": date_str,
                    "source": row.get("source_name", ""),
                    "yoy_change": row.get("yoy_change"),
                    "ytd_change": row.get("ytd_change"),
                    "monthly_trend": row.get("monthly_trend"),
                    "trend_r2": row.get("trend_r2"),
                }
            )
        return formatted
