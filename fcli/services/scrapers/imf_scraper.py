"""
IMF SDMX API scraper for gold reserve data.
Uses the SDMX Python client to fetch official reserve assets data.
"""

import asyncio
import time
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import logging

from .base import BaseScraper, ScraperResult
from ...core.database import GoldReserve
from ...infra.http_client import http_client

logger = logging.getLogger(__name__)


class IMFScraper(BaseScraper):
    """
    IMF SDMX API scraper for gold reserves.
    
    Uses IMF's SDMX 2.1/3.0 API to fetch official reserve assets.
    Data source: IMF International Financial Statistics (IFS)
    """
    
    def __init__(self):
        super().__init__()
        self._source_name = "IMF"
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    async def fetch(self) -> Any:
        try:
            end_date = datetime.now()
            start_date = datetime(end_date.year - 2, end_date.month, 1)
            
            start_period = start_date.strftime("%Y-%m")
            end_period = end_date.strftime("%Y-%m")
            
            countries = [
                ("US", "USA"),
                ("DE", "DEU"),
                ("IT", "ITA"),
                ("FR", "FRA"),
                ("RU", "RUS"),
                ("CN", "CHN"),
                ("CH", "CHE"),
                ("JP", "JPN"),
                ("IN", "IND"),
                ("NL", "NLD"),
                ("TR", "TUR"),
                ("PT", "PRT"),
                ("UZ", "UZB"),
                ("SA", "SAU"),
                ("GB", "GBR"),
                ("KZ", "KAZ"),
                ("ES", "ESP"),
                ("AT", "AUT"),
                ("TH", "THA"),
                ("SG", "SGP"),
            ]
            
            all_data = []
            
            for imf_code, iso_code in countries:
                try:
                    api_url = f"https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/M.{imf_code}.RAF.?startPeriod={start_period}&endPeriod={end_period}"
                    
                    data = await http_client.fetch(api_url)
                    
                    if data and "CompactData" in data:
                        series = data.get("CompactData", {}).get("DataSet", {}).get("Series", {})
                        observations = series.get("Obs", []) if isinstance(series, dict) else []
                        
                        for obs in observations:
                            date_str = obs.get("@TIME_PERIOD", "")
                            value = obs.get("@OBS_VALUE", "")
                            
                            if value and value != "NaN":
                                all_data.append({
                                    "country_code": iso_code,
                                    "country_name": self._get_country_name(iso_code),
                                    "amount": self._parse_value(value),
                                    "date": date_str,
                                })
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch IMF data for {imf_code}: {e}")
                    continue
            
            return {"type": "imf", "data": all_data}
            
        except Exception as e:
            logger.error(f"IMF API fetch failed: {e}")
            return None
    
    def _get_country_name(self, code: str) -> str:
        names = {
            "USA": "United States", "DEU": "Germany", "ITA": "Italy",
            "FRA": "France", "RUS": "Russia", "CHN": "China",
            "CHE": "Switzerland", "JPN": "Japan", "IND": "India",
            "NLD": "Netherlands", "TUR": "Turkey", "PRT": "Portugal",
            "UZB": "Uzbekistan", "SAU": "Saudi Arabia", "GBR": "United Kingdom",
            "KAZ": "Kazakhstan", "ESP": "Spain", "AUT": "Austria",
            "THA": "Thailand", "SGP": "Singapore",
        }
        return names.get(code, code)
    
    def _parse_value(self, value: str) -> float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def parse(self, raw_data: Any) -> List[GoldReserve]:
        if not raw_data or raw_data.get("type") != "imf":
            return []
        
        reserves = []
        fetch_time = datetime.now()
        
        for item in raw_data.get("data", []):
            try:
                report_date = date.today()
                if item.get("date"):
                    try:
                        report_date = datetime.strptime(item["date"], "%Y-%m").date()
                    except ValueError:
                        pass
                
                reserves.append(GoldReserve(
                    country_code=item["country_code"],
                    country_name=item["country_name"],
                    amount_tonnes=item["amount"],
                    percent_of_reserves=None,
                    report_date=report_date,
                    data_source="IMF",
                    fetch_time=fetch_time,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse IMF item: {e}")
                continue
        
        return reserves
