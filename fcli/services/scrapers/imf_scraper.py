"""
IMF SDMX 3.0 API Gold Reserves Scraper
使用 IMF IRFCL (International Reserves and Foreign Currency Liquidity) 数据集
"""

import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp

from fcli.core.config import config
from fcli.infra.http_client import http_client

logger = logging.getLogger(__name__)

IMF_API_BASE = "https://api.imf.org/external/sdmx/3.0"
IL_DATAFLOW = "IMF.STA/IL"
GOLD_INDICATOR = "RGV_REVS"
GOLD_UNIT = "FTO"
GOLD_FREQ = "M"

GOLD_COUNTRY_CODES = {
    "USA": "美国",
    "DEU": "德国",
    "IMF": "国际货币基金组织",
    "ITA": "意大利",
    "FRA": "法国",
    "RUS": "俄罗斯",
    "CHN": "中国",
    "CHE": "瑞士",
    "JPN": "日本",
    "IND": "印度",
    "TUR": "土耳其",
    "NLD": "荷兰",
    "SAU": "沙特阿拉伯",
    "GBR": "英国",
    "LBN": "黎巴嫩",
    "KAZ": "哈萨克斯坦",
    "PRT": "葡萄牙",
    "UZB": "乌兹别克斯坦",
    "AUT": "奥地利",
    "SGP": "新加坡",
    "KOR": "韩国",
    "BRA": "巴西",
    "BEL": "比利时",
    "ARG": "阿根廷",
    "THA": "泰国",
    "VEN": "委内瑞拉",
    "MEX": "墨西哥",
    "SWE": "瑞典",
    "POL": "波兰",
    "AUS": "澳大利亚",
    "PHL": "菲律宾",
    "IDN": "印度尼西亚",
    "MYS": "马来西亚",
    "CAN": "加拿大",
    "ESP": "西班牙",
    "FIN": "芬兰",
    "NOR": "挪威",
    "DNK": "丹麦",
    "CZE": "捷克",
    "HUN": "匈牙利",
    "ROU": "罗马尼亚",
    "GRC": "希腊",
    "ISR": "以色列",
    "EGY": "埃及",
    "ZAF": "南非",
    "NGA": "尼日利亚",
    "VNM": "越南",
}


class IMFScraper:
    """IMF SDMX 3.0 API 黄金储备爬虫"""

    def __init__(self):
        self.api_key = self._get_api_key()
        self.headers = {
            "Accept": "application/json",
        }
        if self.api_key:
            self.headers["Ocp-Apim-Subscription-Key"] = self.api_key

    def _get_api_key(self) -> str | None:
        return config.api.imf_primary

    def _get_proxy(self) -> str | None:
        if config.proxy.enabled:
            return config.proxy.http
        return None

    async def close(self):
        return None

    def _build_data_url(
        self,
        country_code: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> str:
        key = f"{country_code}.{GOLD_INDICATOR}.{GOLD_UNIT}.{GOLD_FREQ}"
        url = f"{IMF_API_BASE}/data/dataflow/{IL_DATAFLOW}/+/{key}"

        params = []
        if start_period:
            params.append(f"c[TIME_PERIOD]=ge:{start_period}")
        if end_period:
            params.append(f"c[TIME_PERIOD]=le:{end_period}")

        if params:
            url += "?" + "&".join(params)

        return url

    async def fetch_gold_reserves(
        self,
        country_code: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> dict:
        url = self._build_data_url(country_code, start_period, end_period)
        proxy = self._get_proxy()

        session = await http_client.get_session()
        timeout = aiohttp.ClientTimeout(total=60, connect=30)

        try:
            async with session.get(url, headers=self.headers, proxy=proxy, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_response(data)
                text = await response.text()
                raise Exception(f"IMF API error: {response.status} - {text}")
        finally:
            await asyncio.sleep(0.3)

    def _parse_response(self, data: dict) -> dict:
        result = {}

        try:
            data_sets = data.get("data", {}).get("dataSets", [])
            structures = data.get("data", {}).get("structures", [])

            if not data_sets:
                logger.debug(f"No dataSets in response, keys: {list(data.keys())}")
                return result

            time_periods = []
            for structure in structures:
                dimensions = structure.get("dimensions", {})
                obs_dims = dimensions.get("observation", [])
                for dim in obs_dims:
                    if dim.get("id") == "TIME_PERIOD":
                        time_periods = [v.get("value") for v in dim.get("values", [])]
                        break

            if not time_periods:
                logger.debug("No TIME_PERIOD dimension found")
                return result

            for data_set in data_sets:
                series = data_set.get("series", {})

                for _series_key, series_data in series.items():
                    observations = series_data.get("observations", {})

                    for obs_idx, obs_value in observations.items():
                        if not obs_value:
                            continue

                        try:
                            raw_value = obs_value[0] if isinstance(obs_value, list) else obs_value
                            if raw_value is None:
                                continue

                            raw_value = float(raw_value)
                            troy_oz_to_kg = 0.0311034768
                            gold_tonnes = raw_value * troy_oz_to_kg / 1000

                            period_idx = int(obs_idx)
                            if period_idx < len(time_periods):
                                period_raw = time_periods[period_idx]
                                if "-M" in str(period_raw):
                                    period = period_raw.replace("-M", "-")
                                else:
                                    period = period_raw

                                if gold_tonnes > 0:
                                    result[period] = round(gold_tonnes, 2)

                        except (ValueError, TypeError, IndexError):
                            continue

        except Exception as e:
            logger.debug(f"Error parsing IMF response: {e}")

        return result

    async def get_latest_gold_reserve(self, country_code: str) -> dict | None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        start_period = start_date.strftime("%Y-%m")
        end_period = end_date.strftime("%Y-%m")

        data = await self.fetch_gold_reserves(country_code, start_period=start_period, end_period=end_period)

        if not data:
            return None

        latest_period = max(data.keys())
        return {
            "period": latest_period,
            "value": data[latest_period],
            "country_code": country_code,
            "country_name": GOLD_COUNTRY_CODES.get(country_code, country_code),
        }

    async def get_gold_reserves_history(self, country_code: str, years: int = 10) -> dict:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        start_period = start_date.strftime("%Y-%m")
        end_period = end_date.strftime("%Y-%m")

        data = await self.fetch_gold_reserves(country_code, start_period=start_period, end_period=end_period)

        logger.debug(f"{country_code}: fetched {len(data)} periods")
        if data:
            sample = list(data.items())[:3]
            logger.debug(f"Sample: {sample}")

        return {
            "country_code": country_code,
            "country_name": GOLD_COUNTRY_CODES.get(country_code, country_code),
            "start_period": start_period,
            "end_period": end_period,
            "data": data,
        }

    async def batch_get_latest_reserves(self, country_codes: list[str] | None = None) -> list[dict]:
        if country_codes is None:
            country_codes = list(GOLD_COUNTRY_CODES.keys())

        tasks = [self.get_latest_gold_reserve(code) for code in country_codes]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"Error fetching {country_codes[i]}: {result}")
            elif result:
                valid_results.append(result)

        valid_results.sort(key=lambda x: x.get("value", 0), reverse=True)

        return valid_results

    async def batch_get_history(self, country_codes: list[str] | None = None, years: int = 10) -> list[dict]:
        if country_codes is None:
            country_codes = list(GOLD_COUNTRY_CODES.keys())

        tasks = [self.get_gold_reserves_history(code, years) for code in country_codes]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"Error fetching history for {country_codes[i]}: {result}")
            elif result and result.get("data"):
                valid_results.append(result)

        return valid_results


async def get_latest_gold(country_code: str) -> dict | None:
    scraper = IMFScraper()
    return await scraper.get_latest_gold_reserve(country_code)


async def get_all_latest_gold() -> list[dict]:
    scraper = IMFScraper()
    return await scraper.batch_get_latest_reserves()


async def get_gold_history(country_code: str, years: int = 10) -> dict:
    scraper = IMFScraper()
    return await scraper.get_gold_reserves_history(country_code, years)


async def get_all_gold_history(years: int = 10) -> list[dict]:
    scraper = IMFScraper()
    return await scraper.batch_get_history(years=years)
