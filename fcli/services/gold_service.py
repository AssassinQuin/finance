"""
Gold reserve service - IMF SDMX 3.0 API only.

Data source: IMF IRFCL (International Reserves and Foreign Currency Liquidity)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..core.config import config
from ..core.database import Database
from ..core.models import GoldReserve
from ..core.stores import GoldReserveStore
from .scrapers.imf_scraper import IMFScraper, GOLD_COUNTRY_CODES

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
    
    async def init_database(self) -> bool:
        """Initialize database connection"""
        return await Database.init(config)
    
    async def close(self):
        """Close HTTP client session"""
        if self._imf_scraper:
            await self._imf_scraper.close()
    
    async def _check_and_update_stale_data(self, country_codes: Optional[List[str]] = None) -> None:
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
            await self.save_to_database(
                country_codes=countries_to_update,
                years=1
            )
    
    async def get_latest(self, country_codes: Optional[List[str]] = None) -> List[Dict]:
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
    async def get_history(
        self, 
        country_code: str, 
        months: int = 120
    ) -> List[Dict]:
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
                history = await GoldReserveStore.get_history(
                    country_code.upper(), 
                    months
                )
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
            data = await self._imf_scraper.get_gold_reserves_history(
                country_code.upper(), 
                years=years
            )
            
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
    async def get_all_history(self, years: int = 10) -> Dict[str, List[Dict]]:
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
    
    async def save_to_database(
        self, 
        country_codes: Optional[List[str]] = None,
        years: int = 10
    ) -> int:
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
        
        results = await self._imf_scraper.batch_get_history(
            country_codes, 
            years=years
        )
        
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
    
    def get_supported_countries(self) -> Dict[str, str]:
        """Get list of supported country codes and names"""
        return GOLD_COUNTRY_CODES.copy()

    async def fetch_all_with_auto_update(self, force: bool = False) -> List[Dict]:
        """
        Fetch all countries' latest gold reserves with auto-update support.
        
        Uses cache/database first, fetches from API if data is stale or force=True.
        
        Args:
            force: Force refresh from API
        
        Returns:
            List of reserve data with change_1m and change_1y fields
        """
        # Try database first (has change calculations)
        if Database.is_enabled() and not force:
            try:
                results = await GoldReserveStore.get_latest_with_changes()
                if results:
                    # Map database fields to expected format
                    return [
                        {
                            "country": r.get("country"),
                            "code": r.get("code"),
                            "amount": r.get("amount"),
                            "date": r.get("date"),
                            "source": r.get("source", "IMF"),
                            "change_1m": r.get("change_1m", 0.0),
                            "change_1y": r.get("change_1y", 0.0),
                        }
                        for r in results
                    ]
            except Exception as e:
                logger.error(f"Failed to get from database: {e}")
        
        # Fetch from IMF API
        logger.info("Fetching latest gold reserves from IMF API...")
        try:
            data = await self._imf_scraper.batch_get_latest_reserves()
            results = [
                {
                    "country": item.get("country_name"),
                    "code": item.get("country_code"),
                    "amount": item.get("value", 0),  # IMF scraper returns tonnes directly
                    "date": item.get("period"),
                    "source": "IMF",
                    "change_1m": 0.0,
                    "change_1y": 0.0,
                }
                for item in data
            ]
            return results
        except Exception as e:
            logger.error(f"Failed to fetch from IMF: {e}")
            return []
    
    async def fetch_global_supply_demand(self) -> Optional[Dict]:
        """
        Fetch global gold supply/demand balance data.
        
        Returns static data based on WGC (World Gold Council) quarterly reports.
        In a production system, this would fetch from WGC API or database.
        
        Returns:
            Dict with supply and demand breakdown
        """
        # Static data based on WGC Q3 2024 report
        # In production, this would come from WGC API or database
        return {
            "date": "2024-Q3",
            "supply": {
                "mine_production": 2976,
                "recycling": 1250,
                "net_hedging": -30,
                "total": 4196,
            },
            "demand": {
                "jewelry": 1958,
                "technology": 382,
                "investment": 1178,
                "central_banks": 693,
                "total": 4211,
            },
        }
    
    async def get_china_history_online(self, months: int = 60) -> List[Dict]:
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
