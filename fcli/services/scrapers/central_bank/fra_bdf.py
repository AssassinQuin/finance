"""
Banque de France scraper for French gold reserves.
Scrapes French central bank gold holdings from their website.
"""

import asyncio
import time
import re
from datetime import datetime, date
from typing import List, Optional
import logging

from ..base import BaseScraper, ScraperResult
from ....core.models import GoldReserve
from ....infra.http_client import http_client

logger = logging.getLogger(__name__)


class BanqueDeFranceScraper(BaseScraper):
    """
    Banque de France scraper for French gold reserve data.

    Source: https://www.banque-france.fr/
    """

    def __init__(self):
        super().__init__()
        self._source_name = "BDF"

    @property
    def source_name(self) -> str:
        return self._source_name

    async def fetch(self) -> Optional[str]:
        """
        Fetch French gold reserve data from Banque de France website.

        Returns:
            Raw HTML response or None if failed
        """
        try:
            # Banque de France monthly monetary statement page
            url = "https://www.banque-france.fr/en/statistics/money/banque-de-france-monthly-monetary-statement"

            html = await http_client.fetch(url, text_mode=True)
            return html

        except Exception as e:
            logger.error(f"Banque de France fetch failed: {e}")
            return None

    def parse(self, raw_data: Optional[str]) -> List[GoldReserve]:
        """
        Parse Banque de France HTML response into GoldReserve objects.

        Args:
            raw_data: HTML response from Banque de France

        Returns:
            List of GoldReserve objects (only France)
        """
        if not raw_data:
            return []

        reserves = []
        fetch_time = datetime.now()

        try:
            # Look for gold reserve data in HTML
            # Banque de France typically shows gold in their monthly statement

            # Try to find gold holdings pattern
            # Pattern: numbers followed by "gold" or "or" (French)
            gold_patterns = [
                r"gold[:\s]+([0-9,\.]+)\s*(?:tonnes?|t)",
                r"or[:\s]+([0-9,\.]+)\s*(?:tonnes?|t)",
                r"([0-9,\.]+)\s*tonnes?\s*(?:of\s+)?gold",
                r"([0-9,\.]+)\s*tonnes?\s*(?:d\'?)?or",
            ]

            amount = None
            for pattern in gold_patterns:
                match = re.search(pattern, raw_data, re.IGNORECASE)
                if match:
                    try:
                        amount_str = match.group(1).replace(",", "")
                        amount = float(amount_str)
                        break
                    except ValueError:
                        continue

            if amount and amount > 0:
                reserves.append(
                    GoldReserve(
                        country_code="FRA",
                        country_name="France",
                        amount_tonnes=amount,
                        percent_of_reserves=None,  # Would need more parsing
                        report_date=date.today(),
                        data_source="BDF",
                        fetch_time=fetch_time,
                    )
                )

        except Exception as e:
            logger.error(f"Failed to parse Banque de France data: {e}")

        return reserves
