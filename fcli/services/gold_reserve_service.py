"""Gold reserve data service.

Provides gold reserve data access with database-first strategy
and IMF API fallback.
"""

from datetime import date, datetime
from typing import Any

from dateutil.relativedelta import relativedelta

from ..core.cache_strategy import CacheStrategyBase
from ..core.database import Database
from ..core.interfaces.cache import CacheABC
from ..core.models.asset import AssetType
from ..core.models.gold import GoldReserve
from ..core.stores.gold import gold_reserve_store
from ..utils.logger import get_logger
from ..utils.time_util import utcnow
from .scrapers.akshare_scraper import AkShareScraper
from .scrapers.imf_scraper import IMFScraper
from .scrapers.ria_scraper import RIAScraper

CACHE_KEY_LATEST = "gold:reserves:latest"


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    return float(v)


logger = get_logger("fcli.gold_reserve")


class GoldReserveService:
    """Service for accessing gold reserve data."""

    def __init__(
        self,
        imf_scraper: IMFScraper,
        cache: CacheABC,
        cache_strategy: CacheStrategyBase,
        akshare_scraper: AkShareScraper | None = None,
        ria_scraper: RIAScraper | None = None,
    ):
        self._imf_scraper = imf_scraper
        self._cache = cache
        self._cache_strategy = cache_strategy
        self._akshare_scraper = akshare_scraper
        self._ria_scraper = ria_scraper

    async def fetch_all_with_auto_update(self, force: bool = False) -> list[dict]:
        """Fetch latest gold reserves with auto-update.

        Main entry point used by CLI commands. Returns presenter-format dicts.

        Uses cache with GOLD TTL (default 24h). Pass force=True to bypass
        cache and force a fresh IMF API fetch.

        Args:
            force: If True, refresh data from IMF before fetching.

        Returns:
            List of dicts with keys: country, code, amount, date, source,
            yoy_change, ytd_change, monthly_trend, trend_r2.
        """
        if not force:
            cached = await self._cache.async_get(CACHE_KEY_LATEST)
            if cached:
                logger.debug("Gold reserves cache hit")
                return cached

        if force:
            await self.save_to_database(years=1)
        else:
            await self._check_and_update_stale_data()

        results = await self._fetch_from_db_or_api()

        if results:
            ttl = self._cache_strategy.get_ttl(AssetType.GOLD)
            await self._cache.async_set(CACHE_KEY_LATEST, results, ttl)

        return results

    async def _fetch_from_db_or_api(self) -> list[dict]:
        """Try DB first, then fall back to online APIs.

        Fallback strategy:
        - CHN: PBOC (AkShare) primary, IMF backup.
        - Other countries: IMF.
        """
        if Database.is_enabled():
            try:
                results = await gold_reserve_store.get_latest_with_stats(
                    min_date=(date.today() + relativedelta(months=-6)).replace(day=1)
                )
                if results:
                    return self._format_stats_results(results)
            except Exception as e:
                logger.warning("DB query failed, falling back to online APIs: %s", e)

        try:
            reserves = await self._imf_scraper.batch_get_latest_reserves()
            results = [
                self._transform_imf_to_dict(
                    country_name=r.country_name,
                    country_code=r.country_code,
                    amount=r.amount_tonnes,
                    period=r.report_date,
                    source=r.data_source or "IMF",
                )
                for r in reserves
            ]

            if self._akshare_scraper:
                try:
                    china_latest = await self._akshare_scraper.get_china_latest()
                    if china_latest:
                        results = [r for r in results if r["code"] != "CHN"]
                        results.append(
                            self._transform_imf_to_dict(
                                country_name=china_latest.country_name,
                                country_code=china_latest.country_code,
                                amount=china_latest.amount_tonnes,
                                period=china_latest.report_date,
                                source="PBOC",
                            )
                        )
                except Exception as e:
                    logger.warning("PBOC fallback for CHN failed, using IMF: %s", e)

            if self._ria_scraper:
                try:
                    russia_latest = await self._ria_scraper.get_russia_latest()
                    if russia_latest and russia_latest.amount_tonnes:
                        results = [r for r in results if r["code"] != "RUS"]
                        results.append(
                            self._transform_imf_to_dict(
                                country_name=russia_latest.country_name,
                                country_code=russia_latest.country_code,
                                amount=russia_latest.amount_tonnes,
                                period=russia_latest.report_date,
                                source="RIA",
                            )
                        )
                except Exception as e:
                    logger.warning("RIA fallback for RUS failed, using IMF: %s", e)

            return results
        except Exception as e:
            if self._akshare_scraper:
                try:
                    china_latest = await self._akshare_scraper.get_china_latest()
                    if china_latest:
                        return [
                            self._transform_imf_to_dict(
                                country_name=china_latest.country_name,
                                country_code=china_latest.country_code,
                                amount=china_latest.amount_tonnes,
                                period=china_latest.report_date,
                                source="PBOC",
                            )
                        ]
                except Exception:
                    pass
            logger.error("All online APIs failed: %s", e)
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
        """Fetch gold reserve history and save to database.

        Strategy:
        - CHN: PBOC (AkShare) primary, IMF backup if PBOC fails.
        - RUS: RIA Novosti primary, IMF backup if RIA fails.
        - Other countries: IMF primary.

        Args:
            country_codes: Optional list of country codes to fetch.
                If None, fetches all supported countries.
            years: Number of years of history to fetch.

        Returns:
            Number of records saved.
        """
        total_saved = 0

        direct_only = country_codes is not None and set(country_codes) <= {"CHN", "RUS"}
        need_china = country_codes is None or "CHN" in (country_codes or [])
        need_russia = country_codes is None or "RUS" in (country_codes or [])

        imf_codes: list[str] = []

        if need_china:
            pboc_saved = await self._update_china_from_pboc(years=years)
            total_saved += pboc_saved
            if pboc_saved == 0:
                logger.warning("PBOC failed for CHN, falling back to IMF")
                imf_codes.append("CHN")

        if need_russia:
            ria_saved = await self._update_russia_from_ria()
            total_saved += ria_saved
            if ria_saved == 0:
                logger.warning("RIA failed for RUS, falling back to IMF")
                imf_codes.append("RUS")

        remaining = [c for c in (country_codes or []) if c not in ("CHN", "RUS")]
        if remaining:
            imf_codes.extend(remaining)

        if not imf_codes and country_codes is None:
            pass
        elif not imf_codes and direct_only:
            return total_saved

        if imf_codes or country_codes is None:
            try:
                fetch_codes = imf_codes if imf_codes else None
                history = await self._imf_scraper.batch_get_history_dict(fetch_codes, years=years)

                if not history:
                    logger.warning("No history data returned from IMF scraper")
                else:
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

                    if reserves:
                        saved = await gold_reserve_store.save_batch(reserves)
                        total_saved += saved
                        logger.info("Saved %d IMF gold reserve records", saved)
            except Exception as e:
                logger.error("Failed to save IMF gold reserves: %s", e)

        return total_saved

    async def _update_china_from_pboc(self, years: int = 10) -> int:
        """Fetch China gold reserves from PBOC via AkShare and save to DB.

        PBOC publishes data faster than IMF (domestic release around the 7th
        of each month vs 1-3 month lag on IMF database).

        Args:
            years: Number of years of history to save.

        Returns:
            Number of records saved, or 0 if AkShare is not configured.
        """
        if not self._akshare_scraper:
            return 0

        try:
            reserves = await self._akshare_scraper.get_china_history()
            if not reserves:
                logger.warning("PBOC (AkShare) returned no China data")
                return 0

            if years < 10:
                cutoff = date.today() - relativedelta(years=years)
                reserves = [r for r in reserves if r.report_date >= cutoff]

            saved = await gold_reserve_store.save_batch(reserves)
            logger.info("Saved %d PBOC China gold reserve records", saved)
            return saved
        except Exception as e:
            logger.warning("PBOC China update failed: %s", e)
            return 0

    async def _update_russia_from_ria(self) -> int:
        """Fetch Russia gold reserves from RIA Novosti and save to DB.

        RIA publishes CBR physical gold volume data (tonnes or million troy
        ounces) shortly after CBR's monthly reserve press release.

        Returns:
            Number of records saved, or 0 if RIA scraper is not configured.
        """
        if not self._ria_scraper:
            return 0

        try:
            reserve = await self._ria_scraper.get_russia_latest()
            if not reserve:
                logger.warning("RIA Novosti returned no Russia data")
                return 0

            saved = await gold_reserve_store.save_batch([reserve])
            logger.info("Saved %d RIA Russia gold reserve record", saved)
            return saved
        except Exception as e:
            logger.warning("RIA Russia update failed: %s", e)
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
            "amount": float(amount) if amount else 0.0,
            "date": period.strftime("%Y-%m") if isinstance(period, date | datetime) else str(period) if period else "",
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
                    "yoy_change": _to_float(row.get("yoy_change")),
                    "ytd_change": _to_float(row.get("ytd_change")),
                    "monthly_trend": _to_float(row.get("monthly_trend")),
                    "trend_r2": _to_float(row.get("trend_r2")),
                }
            )
        return formatted
