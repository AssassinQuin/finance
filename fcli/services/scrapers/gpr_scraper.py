"""GPR (Geopolitical Risk Index) data scraper from Caldara-Iacoviello."""

import asyncio
import logging
from datetime import datetime
from io import BytesIO

import aiohttp
import pandas as pd

from fcli.core.config import config

logger = logging.getLogger(__name__)


class GPRScraper:
    """GPR data scraper from Caldara-Iacoviello dataset."""

    def __init__(self):
        self.data_url = config.datasource.gpr.gpr_data_url
        self._session: aiohttp.ClientSession | None = None
        self._session_lock = asyncio.Lock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    def _get_proxy(self) -> str | None:
        if config.proxy.enabled:
            return config.proxy.http
        return None

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._session_lock:
            if self._session is None or self._session.closed:
                connector = aiohttp.TCPConnector(ssl=False)
                self._session = aiohttp.ClientSession(connector=connector, trust_env=True)
            return self._session

    async def close(self):
        if self._session and not self._session.closed:
            connector = self._session.connector
            await self._session.close()
            if connector and not connector.closed:
                await connector.close()
            self._session = None

    async def fetch_gpr_data(self, start_year: int | None = None) -> dict[str, float]:
        """
        Fetch GPR historical data from Excel file.

        Args:
            start_year: Filter data from this year onwards (optional)

        Returns:
            Dictionary mapping "YYYY-MM" to GPR index value
        """
        session = await self._get_session()
        proxy = self._get_proxy()
        timeout = aiohttp.ClientTimeout(total=120, connect=30)

        async with session.get(self.data_url, proxy=proxy, timeout=timeout) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"GPR data fetch failed: {response.status} - {text}")

            excel_data = await response.read()

        return self._parse_excel(excel_data, start_year)

    def _parse_excel(self, excel_data: bytes, start_year: int | None = None) -> dict[str, float]:
        """
        Parse GPR Excel file.

        Expected format:
        - Column with dates (year-month)
        - Column with GPR index values

        Returns:
            {"2026-01": 135.24, "2025-12": 121.45, ...}
        """
        result = {}

        try:
            df = pd.read_excel(BytesIO(excel_data), sheet_name=0)

            date_col = None
            gpr_col = None

            for col in df.columns:
                col_str = str(col).lower()
                if any(keyword in col_str for keyword in ["date", "month", "year", "time"]):
                    date_col = col
                elif any(keyword in col_str for keyword in ["gpr", "index", "risk"]):
                    gpr_col = col

            if date_col is None or gpr_col is None:
                date_col = df.columns[0]
                gpr_col = df.columns[1]

            for idx, row in df.iterrows():
                try:
                    date_val = row[date_col]
                    gpr_val = row[gpr_col]

                    if pd.isna(date_val) or pd.isna(gpr_val):
                        continue

                    if isinstance(date_val, datetime):
                        period = date_val.strftime("%Y-%m")
                    elif isinstance(date_val, str):
                        if len(date_val) == 7 and "-" in date_val:
                            period = date_val
                        elif len(date_val) == 6:
                            period = f"{date_val[:4]}-{date_val[4:6]}"
                        else:
                            try:
                                dt = pd.to_datetime(date_val)
                                period = dt.strftime("%Y-%m")
                            except Exception:
                                continue
                    else:
                        try:
                            dt = pd.to_datetime(date_val)
                            period = dt.strftime("%Y-%m")
                        except Exception:
                            continue

                    if start_year:
                        year = int(period.split("-")[0])
                        if year < start_year:
                            continue

                    gpr_float = float(gpr_val)

                    if gpr_float > 0:
                        result[period] = round(gpr_float, 2)

                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"Skipping row {idx}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing GPR Excel: {e}")
            raise

        logger.info(f"Parsed {len(result)} GPR data points")
        return result

    async def get_latest_gpr(self) -> dict | None:
        """
        Get the latest GPR index value.

        Returns:
            {"period": "2026-01", "value": 135.24} or None
        """
        data = await self.fetch_gpr_data(start_year=datetime.now().year - 1)

        if not data:
            return None

        latest_period = max(data.keys())
        return {"period": latest_period, "value": data[latest_period]}

    async def get_gpr_history(self, months: int = 12) -> list[dict]:
        """
        Get GPR history for the last N months.

        Args:
            months: Number of months to retrieve

        Returns:
            [{"date": "2026-01", "value": 135.24}, ...]
        """
        start_date = datetime.now()
        start_year = start_date.year - 2

        data = await self.fetch_gpr_data(start_year=start_year)

        sorted_items = sorted(data.items(), reverse=True)[:months]

        return [{"date": date, "value": value} for date, value in sorted_items]


async def fetch_gpr_update() -> dict[str, float]:
    """Fetch all GPR historical data."""
    scraper = GPRScraper()
    try:
        return await scraper.fetch_gpr_data()
    finally:
        await scraper.close()


async def get_latest_gpr() -> dict | None:
    """Get latest GPR value."""
    scraper = GPRScraper()
    try:
        return await scraper.get_latest_gpr()
    finally:
        await scraper.close()
