"""
Bank of Japan scraper for Japanese gold reserves.
Scrapes BOJ website for Japanese gold holdings.
"""

import asyncio
import time
import re
from datetime import datetime, date
from typing import List, Optional
import logging

from ..base import BaseScraper, ScraperResult
from ....core.database import GoldReserve
from ....infra.http_client import http_client

logger = logging.getLogger(__name__)


class BOJScraper(BaseScraper):
    """
    Bank of Japan scraper for Japanese gold reserve data.
    
    Source: https://www.boj.or.jp/
    """
    
    def __init__(self):
        super().__init__()
        self._source_name = "BOJ"
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    async def fetch(self) -> Optional[str]:
        try:
            url = "https://www.boj.or.jp/en/statistics/boj/other/acmai/release/"
            
            html = await http_client.fetch(url, text_mode=True)
            return html
            
        except Exception as e:
            logger.error(f"BOJ fetch failed: {e}")
            return None
    
    def parse(self, raw_data: Optional[str]) -> List[GoldReserve]:
        if not raw_data:
            return []
        
        reserves = []
        fetch_time = datetime.now()
        
        try:
            gold_patterns = [
                r'gold[:\s]+([0-9,\.]+)\s*(?:tonnes?|t)',
                r'([0-9,\.]+)\s*tonnes?\s*(?:of\s+)?gold',
            ]
            
            amount = None
            for pattern in gold_patterns:
                match = re.search(pattern, raw_data, re.IGNORECASE)
                if match:
                    try:
                        amount_str = match.group(1).replace(',', '')
                        amount = float(amount_str)
                        break
                    except ValueError:
                        continue
            
            if amount and amount > 0:
                reserves.append(GoldReserve(
                    country_code="JPN",
                    country_name="Japan",
                    amount_tonnes=amount,
                    percent_of_reserves=None,
                    report_date=date.today(),
                    data_source="BOJ",
                    fetch_time=fetch_time,
                ))
                
        except Exception as e:
            logger.error(f"Failed to parse BOJ data: {e}")
        
        return reserves
