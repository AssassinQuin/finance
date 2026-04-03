"""GPR (Geopolitical Risk Index) data scraper from Caldara-Iacoviello."""

import asyncio
from datetime import datetime
from io import BytesIO

import aiohttp
import pandas as pd

from fcli.core.config import config
from fcli.utils.logger import get_logger

logger = get_logger("fcli.scraper.gpr")

GLOBAL_INDEX_COLUMNS = {
    "GPR": "GPR",
    "GPRT": "GPRT",
    "GPRA": "GPRA",
    "GPRH": "GPRH",
}

GLOBAL_SUB_INDEX_COLUMNS = {
    "GPRHT": "GPRHT",
    "GPRHA": "GPRHA",
    "SHARE_GPR": "SHARE_GPR",
}

COUNTRY_CODE_MAP: dict[str, str] = {
    "GPRC_ARG": "ARG",
    "GPRC_AUS": "AUS",
    "GPRC_BEL": "BEL",
    "GPRC_BRA": "BRA",
    "GPRC_CAN": "CAN",
    "GPRC_CHE": "CHE",
    "GPRC_CHL": "CHL",
    "GPRC_CHN": "CHN",
    "GPRC_COL": "COL",
    "GPRC_DEU": "DEU",
    "GPRC_DNK": "DNK",
    "GPRC_EGY": "EGY",
    "GPRC_ESP": "ESP",
    "GPRC_FIN": "FIN",
    "GPRC_FRA": "FRA",
    "GPRC_GBR": "GBR",
    "GPRC_HKG": "HKG",
    "GPRC_HUN": "HUN",
    "GPRC_IDN": "IDN",
    "GPRC_IND": "IND",
    "GPRC_ISR": "ISR",
    "GPRC_ITA": "ITA",
    "GPRC_JPN": "JPN",
    "GPRC_KOR": "KOR",
    "GPRC_MEX": "MEX",
    "GPRC_MYS": "MYS",
    "GPRC_NLD": "NLD",
    "GPRC_NOR": "NOR",
    "GPRC_PER": "PER",
    "GPRC_PHL": "PHL",
    "GPRC_POL": "POL",
    "GPRC_PRT": "PRT",
    "GPRC_RUS": "RUS",
    "GPRC_SAU": "SAU",
    "GPRC_SWE": "SWE",
    "GPRC_THA": "THA",
    "GPRC_TUN": "TUN",
    "GPRC_TUR": "TUR",
    "GPRC_TWN": "TWN",
    "GPRC_UKR": "UKR",
    "GPRC_USA": "USA",
    "GPRC_VEN": "VEN",
    "GPRC_VNM": "VNM",
    "GPRC_ZAF": "ZAF",
}


def _parse_period(date_val) -> str | None:
    if pd.isna(date_val):
        return None
    if isinstance(date_val, datetime):
        return date_val.strftime("%Y-%m")
    if isinstance(date_val, str):
        if len(date_val) == 7 and "-" in date_val:
            return date_val
        if len(date_val) == 6:
            return f"{date_val[:4]}-{date_val[4:6]}"
        try:
            return pd.to_datetime(date_val).strftime("%Y-%m")
        except (ValueError, TypeError):
            return None
    try:
        return pd.to_datetime(date_val).strftime("%Y-%m")
    except (ValueError, TypeError):
        return None


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

    async def _download_excel(self) -> bytes:
        session = await self._get_session()
        proxy = self._get_proxy()
        timeout = aiohttp.ClientTimeout(total=120, connect=30)

        async with session.get(self.data_url, proxy=proxy, timeout=timeout) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"GPR data fetch failed: {response.status} - {text}")
            return await response.read()

    async def fetch_gpr_data(self, start_year: int | None = None) -> dict[str, float]:
        excel_data = await self._download_excel()
        return self._parse_global_gpr(excel_data, start_year)

    async def fetch_full_data(
        self,
        start_year: int | None = None,
        include_countries: bool = True,
        include_sub_indexes: bool = True,
    ) -> list[dict]:
        """Fetch all GPR data: global indexes + country-specific data.

        Returns:
            List of dicts with keys:
              period, country_code, index_type, value
        """
        excel_data = await self._download_excel()
        return self._parse_full_excel(
            excel_data,
            start_year=start_year,
            include_countries=include_countries,
            include_sub_indexes=include_sub_indexes,
        )

    def _parse_global_gpr(self, excel_data: bytes, start_year: int | None = None) -> dict[str, float]:
        result = {}

        df = pd.read_excel(BytesIO(excel_data), sheet_name=0)
        date_col = "month"

        for _idx, row in df.iterrows():
            period = _parse_period(row.get(date_col))
            if not period:
                continue

            if start_year and int(period[:4]) < start_year:
                continue

            gpr_val = row.get("GPR")
            if pd.isna(gpr_val):
                continue

            val = float(gpr_val)
            if val > 0:
                result[period] = round(val, 2)

        logger.info(f"Parsed {len(result)} global GPR data points")
        return result

    def _parse_full_excel(
        self,
        excel_data: bytes,
        start_year: int | None = None,
        include_countries: bool = True,
        include_sub_indexes: bool = True,
    ) -> list[dict]:
        records = []

        df = pd.read_excel(BytesIO(excel_data), sheet_name=0)
        date_col = "month"

        for _idx, row in df.iterrows():
            period = _parse_period(row.get(date_col))
            if not period:
                continue

            if start_year and int(period[:4]) < start_year:
                continue

            for col_name, index_type in GLOBAL_INDEX_COLUMNS.items():
                val = row.get(col_name)
                if pd.isna(val):
                    continue
                fval = float(val)
                if fval > 0:
                    records.append(
                        {
                            "period": period,
                            "country_code": "WLD",
                            "index_type": index_type,
                            "value": round(fval, 4),
                        }
                    )

            if include_countries:
                for col_name, country_code in COUNTRY_CODE_MAP.items():
                    val = row.get(col_name)
                    if pd.isna(val):
                        continue
                    fval = float(val)
                    if fval > 0:
                        records.append(
                            {
                                "period": period,
                                "country_code": country_code,
                                "index_type": "GPR",
                                "value": round(fval, 4),
                            }
                        )

        logger.info(f"Parsed {len(records)} full GPR data points")
        return records

    async def get_latest_gpr(self) -> dict | None:
        data = await self.fetch_gpr_data(start_year=datetime.now().year - 1)
        if not data:
            return None
        latest_period = max(data.keys())
        return {"period": latest_period, "value": data[latest_period]}

    async def get_gpr_history(self, months: int = 12) -> list[dict]:
        start_year = datetime.now().year - 2
        data = await self.fetch_gpr_data(start_year=start_year)
        sorted_items = sorted(data.items(), reverse=True)[:months]
        return [{"date": d, "value": v} for d, v in sorted_items]
