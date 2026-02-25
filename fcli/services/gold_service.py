"""
Gold reserve service - refactored to use modular scrapers.
Supports multiple data sources: WGC, IMF, and direct central bank scrapers.
"""

import json
import time
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.config import config
from ..core.database import (
    Database,
    GoldReserve,
    GoldReserveStore,
    CentralBankSchedule,
    CentralBankScheduleStore,
    FetchLog,
    FetchLogStore,
)
from ..infra.http_client import http_client
from .scrapers import WGCScraper, IMFScraper, ScraperResult
from .scrapers.central_bank import get_scraper, get_supported_countries

logger = logging.getLogger(__name__)

# Top 20 gold-holding countries
TOP_20_COUNTRIES = [
    {"code": "USA", "name": "美国"},
    {"code": "DEU", "name": "德国"},
    {"code": "ITA", "name": "意大利"},
    {"code": "FRA", "name": "法国"},
    {"code": "RUS", "name": "俄罗斯"},
    {"code": "CHN", "name": "中国"},
    {"code": "CHE", "name": "瑞士"},
    {"code": "JPN", "name": "日本"},
    {"code": "IND", "name": "印度"},
    {"code": "NLD", "name": "荷兰"},
    {"code": "TUR", "name": "土耳其"},
    {"code": "PRT", "name": "葡萄牙"},
    {"code": "UZB", "name": "乌兹别克斯坦"},
    {"code": "SAU", "name": "沙特阿拉伯"},
    {"code": "GBR", "name": "英国"},
    {"code": "KAZ", "name": "哈萨克斯坦"},
    {"code": "ESP", "name": "西班牙"},
    {"code": "AUT", "name": "奥地利"},
    {"code": "THA", "name": "泰国"},
    {"code": "SGP", "name": "新加坡"},
]

# Default fallback data (static)
DEFAULT_RESERVES = [
    {"code": "USA", "country": "美国", "amount": 8133.5, "percent": 67.9},
    {"code": "DEU", "country": "德国", "amount": 3351.6, "percent": 67.9},
    {"code": "ITA", "country": "意大利", "amount": 2451.9, "percent": 58.6},
    {"code": "FRA", "country": "法国", "amount": 2437.0, "percent": 58.9},
    {"code": "RUS", "country": "俄罗斯", "amount": 2333.1, "percent": 24.0},
    {"code": "CHN", "country": "中国", "amount": 2279.6, "percent": 4.3},
    {"code": "CHE", "country": "瑞士", "amount": 1039.9, "percent": 5.2},
    {"code": "JPN", "country": "日本", "amount": 846.0, "percent": 2.5},
    {"code": "IND", "country": "印度", "amount": 876.2, "percent": 8.0},
    {"code": "NLD", "country": "荷兰", "amount": 612.5, "percent": 56.0},
    {"code": "TUR", "country": "土耳其", "amount": 379.1, "percent": 28.0},
    {"code": "PRT", "country": "葡萄牙", "amount": 382.5, "percent": 56.0},
    {"code": "UZB", "country": "乌兹别克斯坦", "amount": 335.9, "percent": 60.0},
    {"code": "SAU", "country": "沙特阿拉伯", "amount": 323.1, "percent": 3.0},
    {"code": "GBR", "country": "英国", "amount": 310.3, "percent": 8.0},
    {"code": "KAZ", "country": "哈萨克斯坦", "amount": 385.5, "percent": 35.0},
    {"code": "ESP", "country": "西班牙", "amount": 281.6, "percent": 17.0},
    {"code": "AUT", "country": "奥地利", "amount": 280.0, "percent": 55.0},
    {"code": "THA", "country": "泰国", "amount": 154.0, "percent": 6.0},
    {"code": "SGP", "country": "新加坡", "amount": 127.4, "percent": 4.0},
]


class GoldService:
    """
    Gold reserve service with multi-source data fetching.
    
    Data source priority (configurable):
    1. WGC Excel (World Gold Council) - Primary source with monthly changes
    2. IMF SDMX API - Validation and backup
    3. Central Bank direct scrapers - Country-specific validation
    """
    
    def __init__(self):
        self.data_file = config.data_dir / "gold_stats.json"
        self._local_data: Dict[str, Any] = {}
        self._load_local_data()
        
        # Initialize scrapers
        self._wgc_scraper = WGCScraper()
        self._imf_scraper = IMFScraper()

    def _load_local_data(self):
        """Load cached data from local JSON file"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self._local_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self._local_data = {}
    
    def _save_local_data(self):
        """Save data to local JSON file"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self._local_data, f, indent=2, ensure_ascii=False)
    
    async def init_database(self) -> bool:
        """Initialize database connection"""
        return await Database.init(config)
    
    def _should_update(
        self, country_code: str, schedule: Optional[CentralBankSchedule]
    ) -> bool:
        """Check if data should be updated based on release schedule"""
        if not schedule or not schedule.release_day:
            return True
        
        today = datetime.now()
        release_day = schedule.release_day
        
        if today.day >= release_day:
            expected_date = today.replace(day=release_day)
            if not Database.is_enabled():
                local_latest = self._local_data.get("reserves", [])
                for r in local_latest:
                    if r.get("code") == country_code:
                        try:
                            latest_date = datetime.strptime(
                                r.get("date", "2000-01"), "%Y-%m"
                            )
                            if latest_date.date() >= expected_date.date():
                                return False
                        except ValueError:
                            pass
                return True
        return False
    
    async def _fetch_from_wgc(self) -> List[Dict]:
        """Fetch data from WGC using the new scraper"""
        logger.info("Fetching gold reserves from WGC...")
        result: ScraperResult = await self._wgc_scraper.scrape()
        
        if result.success and result.data:
            return [
                {
                    "country": r.country_name,
                    "code": r.country_code,
                    "amount": r.amount_tonnes,
                    "percent_of_reserves": r.percent_of_reserves,
                    "date": r.report_date.strftime("%Y-%m"),
                    "source": "WGC",
                }
                for r in result.data
            ]
        
        logger.warning(f"WGC fetch failed: {result.error_message}")
        return []
    
    async def _fetch_from_imf(self) -> List[Dict]:
        """Fetch data from IMF using the new scraper"""
        logger.info("Fetching gold reserves from IMF...")
        result: ScraperResult = await self._imf_scraper.scrape()
        
        if result.success and result.data:
            return [
                {
                    "country": r.country_name,
                    "code": r.country_code,
                    "amount": r.amount_tonnes,
                    "percent_of_reserves": r.percent_of_reserves,
                    "date": r.report_date.strftime("%Y-%m"),
                    "source": "IMF",
                }
                for r in result.data
            ]
        
        logger.warning(f"IMF fetch failed: {result.error_message}")
        return []
    
    async def _fetch_from_central_bank(self, country_code: str) -> Optional[Dict]:
        """Fetch data from a specific central bank"""
        scraper_class = get_scraper(country_code)
        if not scraper_class:
            return None
        
        try:
            scraper = scraper_class()
            result: ScraperResult = await scraper.scrape()
            
            if result.success and result.data:
                r = result.data[0]  # Take first result
                return {
                    "country": r.country_name,
                    "code": r.country_code,
                    "amount": r.amount_tonnes,
                    "percent_of_reserves": r.percent_of_reserves,
                    "date": r.report_date.strftime("%Y-%m"),
                    "source": f"CB_{country_code}",
                }
        except Exception as e:
            logger.warning(f"Central bank scraper for {country_code} failed: {e}")
        
        return None
    
    def _get_default_data(self) -> List[Dict]:
        """Get default fallback data"""
        current_month = datetime.now().strftime("%Y-%m")
        return [
            {
                "country": r["country"],
                "code": r["code"],
                "amount": r["amount"],
                "percent_of_reserves": r["percent"],
                "date": current_month,
                "source": "DEFAULT",
            }
            for r in DEFAULT_RESERVES
        ]
    
    async def fetch_all_with_auto_update(self, force: bool = False) -> List[Dict]:
        """
        Fetch gold reserves with automatic update detection.
        
        Args:
            force: Force update regardless of schedule
            
        Returns:
            List of gold reserve data with changes
        """
        start_time = time.time()
        results = []
        
        # Lazy initialize database
        if not Database.is_enabled():
            await self.init_database()
        
        # Get release schedules
        schedules = {}
        if Database.is_enabled():
            try:
                schedule_list = await CentralBankScheduleStore.get_all_active()
                schedules = {s.country_code: s for s in schedule_list}
            except Exception as e:
                logger.warning(f"Failed to get schedules: {e}")
        
        # Check if update is needed
        need_fetch = force
        if not force:
            for country in TOP_20_COUNTRIES:
                schedule = schedules.get(country["code"])
                if self._should_update(country["code"], schedule):
                    need_fetch = True
                    break
        
        if need_fetch:
            fetched_data = []
            source_used = None
            
            # Try data sources in priority order
            for source in config.source.gold_priority:
                try:
                    if source == "wgc":
                        fetched_data = await self._fetch_from_wgc()
                    elif source == "imf":
                        fetched_data = await self._fetch_from_imf()
                    elif source == "tradingeconomics":
                        # TODO: Implement TradingEconomics scraper
                        continue
                    elif source == "central_bank":
                        # Aggregate from all available central bank scrapers
                        for country_code in get_supported_countries():
                            cb_data = await self._fetch_from_central_bank(country_code)
                            if cb_data:
                                fetched_data.append(cb_data)
                    
                    if fetched_data:
                        source_used = source
                        logger.info(f"Successfully fetched {len(fetched_data)} records from {source}")
                        break
                        
                except Exception as e:
                    logger.error(f"Source {source} failed: {e}")
                    if not config.source.fallback_enabled:
                        raise
                    continue
            
            # Process fetched data
            if fetched_data:
                if Database.is_enabled():
                    try:
                        reserves = [
                            GoldReserve(
                                country_code=d["code"],
                                country_name=d["country"],
                                amount_tonnes=d["amount"],
                                percent_of_reserves=d.get("percent_of_reserves"),
                                report_date=datetime.strptime(d["date"], "%Y-%m").date(),
                                data_source=d["source"],
                                fetch_time=datetime.now(),
                            )
                            for d in fetched_data
                        ]
                        await GoldReserveStore.save_batch(reserves)
                        
                        # Log successful fetch
                        await FetchLogStore.log(
                            FetchLog(
                                data_type="gold_reserves",
                                source=source_used or "unknown",
                                status="success",
                                records_count=len(fetched_data),
                                duration_ms=int((time.time() - start_time) * 1000),
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to save to database: {e}")
                else:
                    # Save to local file
                    self._local_data["reserves"] = fetched_data
                    self._local_data["last_update"] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    self._save_local_data()
            else:
                # Use default data
                logger.warning("All sources failed, using default data")
                fetched_data = self._get_default_data()
                if not Database.is_enabled():
                    self._local_data["reserves"] = fetched_data
                    self._save_local_data()
        
        # Get results with changes
        if Database.is_enabled():
            try:
                db_results = await GoldReserveStore.get_latest_with_changes()
                results = [
                    {
                        "country": r["country"],
                        "code": r["code"],
                        "amount": r["amount"],
                        "percent_of_reserves": r.get("percent_of_reserves"),
                        "date": r["date"],
                        "source": r["source"],
                        "change_1m": r.get("change_1m", 0.0),
                        "change_1y": r.get("change_1y", 0.0),
                    }
                    for r in db_results
                ]
            except Exception as e:
                logger.error(f"Failed to get results from database: {e}")
                results = self._local_data.get("reserves", [])
        else:
            results = self._local_data.get("reserves", [])
        
        if not results:
            results = self._get_default_data()
        
        return sorted(results, key=lambda x: x.get("amount", 0), reverse=True)
    
    async def fetch_imf_reserves(self, countries: List[str]) -> List[Dict]:
        """Fetch IMF reserves for specific countries"""
        return await self.fetch_all_with_auto_update()
    
    async def fetch_global_supply_demand(self) -> Dict:
        """
        Fetch global gold supply/demand data.
        TODO: Implement scraping from WGC quarterly reports.
        """
        return {
            "date": "2025 Q4",
            "supply": {
                "mine_production": 927.3,
                "recycling": 288.6,
                "net_hedging": 1.2,
                "total": 1217.1,
            },
            "demand": {
                "jewelry": 516.2,
                "technology": 82.5,
                "investment": 156.9,
                "central_banks": 337.1,
                "total": 1092.7,
            },
        }
    
    async def get_history(self, country_code: str, months: int = 24) -> List[Dict]:
        """
        Get historical gold reserves for a country.
        
        Args:
            country_code: ISO 3-letter country code
            months: Number of months of history to return
            
        Returns:
            List of historical reserve data
        """
        if Database.is_enabled():
            try:
                history = await GoldReserveStore.get_history(country_code.upper(), months)
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
        
        # Fallback to default history data
        default_history = [
            {"code": "USA", "country": "美国", "amount": 8133.46, "date": "2026-01"},
            {"code": "USA", "country": "美国", "amount": 8133.46, "date": "2025-12"},
            {"code": "USA", "country": "美国", "amount": 8133.46, "date": "2025-11"},
            {"code": "CHN", "country": "中国", "amount": 2264.12, "date": "2026-01"},
            {"code": "CHN", "country": "中国", "amount": 2264.12, "date": "2025-12"},
            {"code": "CHN", "country": "中国", "amount": 2235.39, "date": "2025-11"},
        ]
        return [h for h in default_history if h["code"] == country_code.upper()]


# Singleton instance
gold_service = GoldService()
