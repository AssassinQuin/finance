"""
Federal Reserve Economic Data (FRED) scraper for US gold reserves.
Uses the FRED API to fetch US official gold holdings.
"""

import asyncio
import time
from datetime import datetime, date
from typing import List, Optional
import logging

from ..base import BaseScraper, ScraperResult
from ....core.models import GoldReserve
from ....infra.http_client import http_client

logger = logging.getLogger(__name__)


class FREDSscraper(BaseScraper):
    """
    FRED API scraper for US gold reserve data.
    
    Uses the Federal Reserve Economic Data API.
    Series ID: TRESEGYM (Treasury's Gold Holdings)
    """
    
    def __init__(self):
        super().__init__()
        self._source_name = "FRED"
        self.series_id = "TRESEGYM"
        self.fred_api_key = None
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    async def fetch(self) -> Optional[dict]:
        try:
            api_key = self.fred_api_key or "fred"
            
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": self.series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": self._get_start_date(),
                "observation_end": datetime.now().strftime("%Y-%m-%d"),
            }
            
            response = await http_client.fetch(url, params=params)
            return response
            
        except Exception as e:
            logger.error(f"FRED API fetch failed: {e}")
            return None
    
    def _get_start_date(self) -> str:
        from datetime import timedelta
        start = datetime.now() - timedelta(days=730)
        return start.strftime("%Y-%m-%d")
    
    def parse(self, raw_data: Optional[dict]) -> List[GoldReserve]:
        if not raw_data:
            return []
        
        reserves = []
        fetch_time = datetime.now()
        
        try:
            observations = raw_data.get("observations", [])
            
            for obs in observations[-24:]:
                try:
                    date_str = obs.get("date", "")
                    value = obs.get("value", "")
                    
                    if value and value != ".":
                        amount_troy_oz = float(value) * 1_000_000
                        amount_tonnes = amount_troy_oz / 32150.74656
                        
                        report_date = date.today()
                        if date_str:
                            try:
                                report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            except ValueError:
                                pass
                        
                        reserves.append(GoldReserve(
                            country_code="USA",
                            country_name="United States",
                            amount_tonnes=round(amount_tonnes, 2),
                            percent_of_reserves=None,
                            report_date=report_date,
                            data_source="FRED",
                            fetch_time=fetch_time,
                        ))
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse FRED observation: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to parse FRED data: {e}")
        
        return reserves
