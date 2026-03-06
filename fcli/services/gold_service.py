"""
Gold reserve service - IMF SDMX 3.0 API only.

Data source: IMF IRFCL (International Reserves and Foreign Currency Liquidity)
"""

import logging
from datetime import datetime

from ..core.config import config
from ..core.database import Database
from ..core.models import GoldReserve
from ..core.models.gold_supply_demand import GoldSupplyDemand
from ..core.stores import GoldReserveStore
from ..core.stores.gold_supply_demand import GoldSupplyDemandStore
from .scrapers.imf_scraper import GOLD_COUNTRY_CODES, IMFScraper
from .scrapers.wgc_scraper import WGCScraper

logger = logging.getLogger(__name__)


class GoldService:
    """
    Gold reserve service using IMF SDMX 3.0 API.

    Data source: IMF IRFCL dataset
    - Gold reserves in USD (converted to tonnes)
    - Monthly data for 40+ countries
    - 10+ years of history
    """

    def __init__(self):
        self._imf_scraper = IMFScraper()
        self._wgc_scraper = WGCScraper()

    async def init_database(self) -> bool:
        """Initialize database connection"""
        return await Database.init(config)

    async def close(self) -> None:
        """Close HTTP client sessions"""
        if self._imf_scraper:
            await self._imf_scraper.close()
        if self._wgc_scraper:
            await self._wgc_scraper.close()
        # Close global http_client singleton
        from ..infra.http_client import http_client

        await http_client.close()

    async def _check_and_update_stale_data(self, country_codes: list[str] | None = None) -> None:
        """
        检查并更新过期的数据。

        如果某个国家的数据不是最新上一个月的，自动从 IMF 更新。
        """
        if not Database.is_enabled():
            return

        from datetime import date

        from dateutil.relativedelta import relativedelta

        # 计算上个月的日期（目标日期）
        today = date.today()
        last_month = today - relativedelta(months=1)
        target_date = date(last_month.year, last_month.month, 1)

        # 获取所有国家的最新数据日期
        latest_dates = await GoldReserveStore.get_all_latest_dates()

        # 找出需要更新的国家
        countries_to_update = []

        if country_codes:
            # 检查指定的国家
            for code in country_codes:
                code_upper = code.upper()
                if code_upper not in latest_dates:
                    # 数据库中没有这个国家的数据
                    countries_to_update.append(code_upper)
                elif latest_dates[code_upper] < target_date:
                    # 数据不是上个月的
                    countries_to_update.append(code_upper)
        else:
            # 检查所有支持的国家
            for code in GOLD_COUNTRY_CODES.keys():
                if code not in latest_dates:
                    countries_to_update.append(code)
                elif latest_dates[code] < target_date:
                    countries_to_update.append(code)

        if countries_to_update:
            logger.info(f"Auto-updating {len(countries_to_update)} countries with stale data...")
            # 只获取最新数据（1个月）
            await self.save_to_database(country_codes=countries_to_update, years=1)

    async def get_latest(self, country_codes: list[str] | None = None) -> list[dict]:
        """
        Get latest gold reserves for countries.

        自动检查并更新过期数据：
        - 如果数据库中没有该国家数据，自动获取
        - 如果数据不是最新上一个月的，自动更新

        Args:
            country_codes: List of ISO 3-letter country codes (optional)

        Returns:
            List of latest reserve data sorted by amount descending
        """
        # 先检查并更新过期数据
        await self._check_and_update_stale_data(country_codes)

        # Try database first
        if Database.is_enabled():
            try:
                results = await GoldReserveStore.get_latest_with_changes()
                if results:
                    if country_codes:
                        results = [r for r in results if r.get("code") in country_codes]
                    return results
            except Exception as e:
                logger.error(f"Failed to get from database: {e}")

        # Fetch from IMF API
        logger.info("Fetching latest gold reserves from IMF API...")
        try:
            data = await self._imf_scraper.batch_get_latest_reserves(country_codes)
            return [
                {
                    "country": item.get("country_name"),
                    "code": item.get("country_code"),
                    "amount": item.get("value", 0),  # IMF scraper returns tonnes directly
                    "date": item.get("period"),
                    "source": "IMF",
                }
                for item in data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch from IMF: {e}")
            return []

    async def get_history(self, country_code: str, months: int = 120) -> list[dict]:
        """
        Get historical gold reserves for a country.

        Args:
            country_code: ISO 3-letter country code
            months: Number of months of history (default 120 = 10 years)

        Returns:
            List of historical reserve data
        """
        # Try database first
        if Database.is_enabled():
            try:
                history = await GoldReserveStore.get_history(country_code.upper(), months)
                if history:
                    return [
                        {
                            "country": r.country_name,
                            "code": r.country_code,
                            "amount": r.amount_tonnes,
                            "date": r.report_date.strftime("%Y-%m"),
                            "source": r.data_source,
                        }
                        for r in history
                    ]
            except Exception as e:
                logger.error(f"Failed to get history from database: {e}")

        # Fetch from IMF API
        logger.info(f"Fetching gold reserves history for {country_code} from IMF...")
        try:
            years = max(1, months // 12)
            data = await self._imf_scraper.get_gold_reserves_history(country_code.upper(), years=years)

            result = [
                {
                    "country": data.get("country_name"),
                    "code": data.get("country_code"),
                    "amount": value,  # IMF scraper returns tonnes directly, no conversion needed
                    "date": period,
                    "source": "IMF",
                }
                for period, value in data.get("data", {}).items()
            ]
            return result
        except Exception as e:
            logger.error(f"Failed to get history from IMF: {e}")
            return []

    async def get_all_history(self, years: int = 10) -> dict[str, list[dict]]:
        """
        Get historical gold reserves for all countries.

        Args:
            years: Number of years of history

        Returns:
            Dict mapping country_code to list of historical data
        """
        logger.info(f"Fetching {years} years of history for all countries...")

        results = await self._imf_scraper.batch_get_history(years=years)

        output = {}
        for country_data in results:
            code = country_data.get("country_code")
            history = [
                {
                    "country": country_data.get("country_name"),
                    "code": code,
                    "amount": value,  # IMF scraper returns tonnes directly
                    "date": period,
                    "source": "IMF",
                }
                for period, value in country_data.get("data", {}).items()
            ]
            history.sort(key=lambda x: x["date"], reverse=True)
            output[code] = history

        return output

    async def save_to_database(self, country_codes: list[str] | None = None, years: int = 10) -> int:
        """
        Save gold reserves to database.

        Args:
            country_codes: List of country codes (optional, all if not specified)
            years: Years of history to save

        Returns:
            Number of records saved
        """
        if not Database.is_enabled():
            logger.warning("Database not enabled")
            return 0

        logger.info(f"Fetching {years} years of history for saving...")

        results = await self._imf_scraper.batch_get_history(country_codes, years=years)

        reserves = []
        fetch_time = datetime.now()

        for country_data in results:
            code = country_data.get("country_code")
            name = country_data.get("country_name", code)

            for period, value in country_data.get("data", {}).items():
                try:
                    report_date = datetime.strptime(period, "%Y-%m").date()
                except ValueError:
                    continue

                reserve = GoldReserve(
                    country_code=code,
                    country_name=name,
                    amount_tonnes=value,  # IMF scraper returns tonnes directly
                    percent_of_reserves=None,
                    report_date=report_date,
                    data_source="IMF",
                    fetch_time=fetch_time,
                )
                reserves.append(reserve)

        if not reserves:
            return 0

        saved = await GoldReserveStore.save_batch(reserves)
        logger.info(f"Saved {saved} records to database")

        return saved

    def _usd_to_tonnes(self, usd_millions: float) -> float:
        """
        DEPRECATED: This function should NOT be used for IMF data.

        IMF scraper already returns values in tonnes directly.
        This function is kept for potential future use with USD-based data sources.

        Convert gold reserves from million USD to tonnes.
        Uses approximate gold price of $2300/oz (2024 average).

        Args:
            usd_millions: Value in million USD

        Returns:
            Tonnes of gold
        """
        if not usd_millions or usd_millions <= 0:
            return 0.0

        GOLD_PRICE_USD_PER_OUNCE = config.gold.price_usd_per_ounce
        GRAMS_PER_OUNCE = 31.1035

        usd = usd_millions * 1_000_000
        ounces = usd / GOLD_PRICE_USD_PER_OUNCE
        grams = ounces * GRAMS_PER_OUNCE
        tonnes = grams / 1_000_000

        return round(tonnes, 2)

    def get_supported_countries(self) -> dict[str, str]:
        """Get list of supported country codes and names"""
        return GOLD_COUNTRY_CODES.copy()

    async def fetch_all_with_auto_update(self, force: bool = False) -> list[dict]:
        """
        Fetch all countries' latest gold reserves with auto-update support.

        自动检查并更新过期数据，返回多时间段变化 (1m, 3m, 6m, 12m)。

        Args:
            force: Force refresh from API

        Returns:
            List of reserve data with change_1m, change_3m, change_6m, change_12m fields
        """
        # 如果强制更新，先从 IMF 获取数据
        if force:
            logger.info("Force updating from IMF API...")
            await self.save_to_database(years=1)
        else:
            # 自动检查并更新过期数据
            await self._check_and_update_stale_data()

        # 从数据库获取多时间段变化数据
        if Database.is_enabled():
            try:
                results = await GoldReserveStore.get_latest_with_multi_period_changes()
                if results:
                    return [
                        {
                            "country": r.get("country"),
                            "code": r.get("code"),
                            "amount": r.get("amount"),
                            "date": str(r.get("date")) if r.get("date") else None,
                            "source": r.get("source", "IMF"),
                            "change_1m": r.get("change_1m", 0.0) or 0.0,
                            "change_3m": r.get("change_3m", 0.0) or 0.0,
                            "change_6m": r.get("change_6m", 0.0) or 0.0,
                            "change_12m": r.get("change_12m", 0.0) or 0.0,
                        }
                        for r in results
                    ]
            except Exception as e:
                logger.error(f"Failed to get from database: {e}")

        # 无数据库，直接从 IMF 获取
        logger.info("Fetching latest gold reserves from IMF API...")
        try:
            data = await self._imf_scraper.batch_get_latest_reserves()
            return [
                {
                    "country": item.get("country_name"),
                    "code": item.get("country_code"),
                    "amount": item.get("value", 0),
                    "date": item.get("period"),
                    "source": "IMF",
                    "change_1m": 0.0,
                    "change_3m": 0.0,
                    "change_6m": 0.0,
                    "change_12m": 0.0,
                }
                for item in data
            ]
        except Exception as e:
            logger.error(f"Failed to fetch from IMF: {e}")
            return []

    async def fetch_global_supply_demand(self, force_update: bool = False) -> dict | None:
        """
        Fetch global gold supply/demand balance data from WGC.

        Data source: World Gold Council (gold.org)
        - Quarterly supply/demand statistics
        - Mine production, recycling, hedging (supply)
        - Jewelry, technology, investment, central banks (demand)

        Args:
            force_update: Force refresh from WGC and save to database

        Returns:
            Dict with supply and demand breakdown, or None if unavailable
        """
        # Try database first (unless force update)
        if not force_update and Database.is_enabled():
            try:
                db_data = await GoldSupplyDemandStore.get_latest()
                if db_data:
                    return self._supply_demand_to_dict(db_data)
            except Exception as e:
                logger.error(f"Failed to get supply/demand from database: {e}")

        # Fetch from WGC
        try:
            data = await self._wgc_scraper.fetch_supply_demand()
            if not data:
                return None

            # Save to database if enabled
            if Database.is_enabled():
                try:
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
                    logger.info(f"Saved supply/demand data for {data.period} to database")
                except Exception as e:
                    logger.error(f"Failed to save supply/demand to database: {e}")

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
        except Exception as e:
            logger.error(f"Failed to fetch supply/demand data: {e}")
            return None

    def _supply_demand_to_dict(self, db_data: GoldSupplyDemand) -> dict:
        """Convert database model to API dict format."""
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
        """
        Get historical supply/demand data from database.

        Args:
            limit: Number of quarters to return (default 8 = 2 years)

        Returns:
            List of supply/demand data by quarter (newest first)
        """
        if not Database.is_enabled():
            return []

        try:
            history = await GoldSupplyDemandStore.get_history(limit)
            return [self._supply_demand_to_dict(item) for item in history]
        except Exception as e:
            logger.error(f"Failed to get supply/demand history: {e}")
            return []

    async def get_supply_demand_by_quarter(self, year: int, quarter: int) -> dict | None:
        """
        Get supply/demand data for a specific quarter.

        Args:
            year: Year (e.g. 2024)
            quarter: Quarter (1-4)

        Returns:
            Supply/demand data or None if not found
        """
        if not Database.is_enabled():
            return None

        try:
            data = await GoldSupplyDemandStore.get_by_quarter(year, quarter)
            if data:
                return self._supply_demand_to_dict(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get supply/demand for {year}Q{quarter}: {e}")
            return None

    async def get_china_history_online(self, months: int = 60) -> list[dict]:
        """
        Get China's gold reserve history from IMF API.

        Args:
            months: Number of months of history (default 60 = 5 years)

        Returns:
            List of historical data with date and amount
        """
        history = await self.get_history("CHN", months=months)
        return [
            {
                "date": h["date"],
                "amount": h["amount"],
            }
            for h in history
        ]


# Singleton instance
gold_service = GoldService()
