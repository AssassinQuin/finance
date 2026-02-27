"""
Base scraper class for gold reserve data.
Provides common functionality for all scrapers.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from ...core.models import GoldReserve


@dataclass
class ScraperResult:
    """Result from a scraper operation"""
    success: bool
    data: List[GoldReserve] = field(default_factory=list)
    source: str = ""
    error_message: Optional[str] = None
    fetch_time_ms: int = 0
    records_count: int = 0
    
    def __post_init__(self):
        if self.data:
            self.records_count = len(self.data)


class BaseScraper(ABC):
    """
    Abstract base class for gold reserve scrapers.
    
    Subclasses must implement:
    - fetch(): Async method to fetch raw data
    - parse(): Method to parse raw data into GoldReserve objects
    - source_name: Property returning the source name
    """
    
    def __init__(self):
        self._last_fetch_time: Optional[datetime] = None
        self._cache: Dict[str, Any] = {}
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source"""
        pass
    
    @abstractmethod
    async def fetch(self) -> Any:
        """
        Fetch raw data from the source.
        Returns raw data that can be parsed.
        """
        pass
    
    @abstractmethod
    def parse(self, raw_data: Any) -> List[GoldReserve]:
        """
        Parse raw data into GoldReserve objects.
        
        Args:
            raw_data: Raw data from fetch()
            
        Returns:
            List of GoldReserve objects
        """
        pass
    
    async def scrape(self) -> ScraperResult:
        """
        Main entry point: fetch and parse data.
        
        Returns:
            ScraperResult with success status and data
        """
        start_time = time.time()
        
        try:
            raw_data = await self.fetch()
            
            if raw_data is None:
                return ScraperResult(
                    success=False,
                    source=self.source_name,
                    error_message="No data returned from fetch",
                    fetch_time_ms=int((time.time() - start_time) * 1000),
                )
            
            reserves = self.parse(raw_data)
            
            self._last_fetch_time = datetime.now()
            
            return ScraperResult(
                success=True,
                data=reserves,
                source=self.source_name,
                fetch_time_ms=int((time.time() - start_time) * 1000),
            )
            
        except Exception as e:
            return ScraperResult(
                success=False,
                source=self.source_name,
                error_message=str(e),
                fetch_time_ms=int((time.time() - start_time) * 1000),
            )
    
    @staticmethod
    def country_name_to_code(name: str) -> str:
        """
        Convert country name to ISO 3-letter code.
        
        Args:
            name: Country name (English or Chinese)
            
        Returns:
            ISO 3-letter country code
        """
        name_map = {
            # English names
            "United States": "USA",
            "Germany": "DEU",
            "Italy": "ITA",
            "France": "FRA",
            "Russia": "RUS",
            "China": "CHN",
            "Switzerland": "CHE",
            "Japan": "JPN",
            "India": "IND",
            "Netherlands": "NLD",
            "Turkey": "TUR",
            "Portugal": "PRT",
            "Uzbekistan": "UZB",
            "Saudi Arabia": "SAU",
            "United Kingdom": "GBR",
            "UK": "GBR",
            "Kazakhstan": "KAZ",
            "Spain": "ESP",
            "Austria": "AUT",
            "Thailand": "THA",
            "Singapore": "SGP",
            "Brazil": "BRA",
            "Mexico": "MEX",
            "Canada": "CAN",
            "Australia": "AUS",
            "South Korea": "KOR",
            "Korea": "KOR",
            "Poland": "POL",
            "Belgium": "BEL",
            "Sweden": "SWE",
            "South Africa": "ZAF",
            "Egypt": "EGY",
            "Argentina": "ARG",
            "Philippines": "PHL",
            "Malaysia": "MYS",
            "Indonesia": "IDN",
            "Vietnam": "VNM",
            # Chinese names
            "美国": "USA",
            "德国": "DEU",
            "意大利": "ITA",
            "法国": "FRA",
            "俄罗斯": "RUS",
            "中国": "CHN",
            "瑞士": "CHE",
            "日本": "JPN",
            "印度": "IND",
            "荷兰": "NLD",
            "土耳其": "TUR",
            "葡萄牙": "PRT",
            "乌兹别克斯坦": "UZB",
            "乌兹别克": "UZB",
            "沙特阿拉伯": "SAU",
            "沙特": "SAU",
            "英国": "GBR",
            "哈萨克斯坦": "KAZ",
            "哈萨克": "KAZ",
            "西班牙": "ESP",
            "奥地利": "AUT",
            "泰国": "THA",
            "新加坡": "SGP",
            "巴西": "BRA",
            "墨西哥": "MEX",
            "加拿大": "CAN",
            "澳大利亚": "AUS",
            "韩国": "KOR",
            "波兰": "POL",
            "比利时": "BEL",
            "瑞典": "SWE",
            "南非": "ZAF",
            "埃及": "EGY",
            "阿根廷": "ARG",
            "菲律宾": "PHL",
            "马来西亚": "MYS",
            "印度尼西亚": "IDN",
            "越南": "VNM",
        }
        
        # Direct lookup
        if name in name_map:
            return name_map[name]
        
        # Try case-insensitive match
        name_lower = name.lower()
        for key, value in name_map.items():
            if key.lower() == name_lower:
                return value
        
        # Fallback: first 3 letters uppercase
        return name[:3].upper()
    
    @staticmethod
    def code_to_country_name(code: str) -> str:
        """
        Convert ISO 3-letter code to Chinese country name.
        
        Args:
            code: ISO 3-letter country code
            
        Returns:
            Chinese country name
        """
        code_map = {
            "USA": "美国",
            "DEU": "德国",
            "ITA": "意大利",
            "FRA": "法国",
            "RUS": "俄罗斯",
            "CHN": "中国",
            "CHE": "瑞士",
            "JPN": "日本",
            "IND": "印度",
            "NLD": "荷兰",
            "TUR": "土耳其",
            "PRT": "葡萄牙",
            "UZB": "乌兹别克斯坦",
            "SAU": "沙特阿拉伯",
            "GBR": "英国",
            "KAZ": "哈萨克斯坦",
            "ESP": "西班牙",
            "AUT": "奥地利",
            "THA": "泰国",
            "SGP": "新加坡",
            "BRA": "巴西",
            "MEX": "墨西哥",
            "CAN": "加拿大",
            "AUS": "澳大利亚",
            "KOR": "韩国",
            "POL": "波兰",
            "BEL": "比利时",
            "SWE": "瑞典",
            "ZAF": "南非",
            "EGY": "埃及",
            "ARG": "阿根廷",
            "PHL": "菲律宾",
            "MYS": "马来西亚",
            "IDN": "印度尼西亚",
            "VNM": "越南",
        }
        return code_map.get(code.upper(), code)
