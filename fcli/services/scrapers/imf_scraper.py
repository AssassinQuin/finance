"""
IMF SDMX 3.0 API Gold Reserves Scraper.

Uses IMF IRFCL (International Reserves and Foreign Currency Liquidity) dataset.
API Documentation: https://data.imf.org/

Unit Conversion:
  - IMF reports gold reserves in troy ounces
  - 1 troy ounce = 0.0311034768 kg (exact)
  - 1 tonne = 1000 kg
  - Therefore: troy_oz × 0.0311034768 / 1000 = tonnes
"""

from __future__ import annotations

import asyncio
import random
import socket

import aiohttp
from dateutil.relativedelta import relativedelta

from fcli.core.config import Settings
from fcli.core.models.base import SOURCE_IMF
from fcli.core.models.gold import GoldReserve
from fcli.infra.http_client import HttpClient
from fcli.utils.logger import get_logger
from fcli.utils.time_util import MONTH_FORMAT, utcnow

logger = get_logger("fcli.scraper.imf")

# Errors that indicate non-transient network issues (DNS, connection refused, etc.)
# Retrying these is pointless — they won't resolve within seconds.
DNS_ERROR_MARKERS = (
    "DNS server returned",
    "Name or service not known",
    "nodename nor servname",
    "getaddrinfo failed",
    "Temporary failure in name resolution",
    "No route to host",
)


def _is_dns_error(exc: BaseException) -> bool:
    """Check if an exception is caused by a DNS resolution failure.

    Note: We only check socket.gaierror, NOT OSError broadly.
    aiohttp.ClientOSError inherits from OSError but represents connection
    errors (like "Connection reset by peer") that ARE retryable — unlike
    true DNS failures which won't resolve within seconds.
    """
    if isinstance(exc, socket.gaierror):
        return True
    msg = str(exc).lower()
    return any(marker.lower() in msg for marker in DNS_ERROR_MARKERS)


class IMFScraper:
    """IMF SDMX 3.0 API Gold Reserves Scraper with exponential backoff."""

    IMF_API_BASE = "https://api.imf.org/external/sdmx/3.0"
    IL_DATAFLOW = "IMF.STA/IL"
    GOLD_INDICATOR = "RGV_REVS"
    GOLD_UNIT = "FTO"
    GOLD_FREQ = "M"

    TROY_OZ_TO_KG = 0.0311034768
    KG_TO_TONNES = 1000

    BASE_DELAY = 0.5
    MAX_DELAY = 30.0
    MAX_RETRIES = 3
    DNS_FAIL_THRESHOLD = 3  # consecutive DNS failures before circuit breaks

    GOLD_COUNTRY_CODES: dict[str, str] = {
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

    def __init__(
        self,
        http_client: HttpClient,
        settings: Settings,
        country_codes: dict[str, str] | None = None,
    ):
        self._http_client = http_client
        self._config = settings
        self.api_key = self._get_api_key()
        self.headers = {"Accept": "application/json"}
        if self.api_key:
            self.headers["Ocp-Apim-Subscription-Key"] = self.api_key
        self.country_codes = country_codes or self.GOLD_COUNTRY_CODES
        self._consecutive_dns_failures = 0
        self._dns_circuit_open = False
        self._semaphore = asyncio.Semaphore(self._config.datasource.gold.imf_batch_concurrency)

    def _get_api_key(self) -> str | None:
        return self._config.api.imf_primary

    def _get_proxy(self, url: str) -> str | None:
        if not self._config.proxy.enabled:
            return None
        if url.startswith("https://"):
            return self._config.proxy.https or self._config.proxy.http
        return self._config.proxy.http

    async def close(self):
        pass

    def _build_data_url(
        self,
        country_code: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> str:
        key = f"{country_code}.{self.GOLD_INDICATOR}.{self.GOLD_UNIT}.{self.GOLD_FREQ}"
        url = f"{self.IMF_API_BASE}/data/dataflow/{self.IL_DATAFLOW}/+/{key}"

        params = []
        if start_period:
            params.append(f"c[TIME_PERIOD]=ge:{start_period}")
        if end_period:
            params.append(f"c[TIME_PERIOD]=le:{end_period}")

        if params:
            url += "?" + "&".join(params)

        return url

    async def _request_with_backoff(self, url: str) -> dict:
        if self._dns_circuit_open:
            raise aiohttp.ClientError("DNS circuit breaker open — skipping request")

        for attempt in range(self.MAX_RETRIES):
            try:
                session = await self._http_client.get_session()
                timeout = aiohttp.ClientTimeout(
                    total=self._config.datasource.gold.imf_timeout_total,
                    connect=self._config.datasource.gold.imf_timeout_connect,
                )
                proxy = self._get_proxy(url)

                async with self._semaphore:
                    async with session.get(url, headers=self.headers, proxy=proxy, timeout=timeout) as response:
                        if response.status == 200:
                            self._consecutive_dns_failures = 0
                            return await response.json()
                        if response.status == 429:
                            retry_after = float(response.headers.get("Retry-After", "5"))
                            await asyncio.sleep(retry_after)
                            continue
                        text = await response.text()
                        raise aiohttp.ClientError(f"IMF API error: {response.status} - {text}")

            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
                if _is_dns_error(e):
                    self._consecutive_dns_failures += 1
                    if self._consecutive_dns_failures >= self.DNS_FAIL_THRESHOLD:
                        self._dns_circuit_open = True
                        logger.error(
                            "DNS failed %d times consecutively — circuit breaker open, skipping remaining requests",
                            self._consecutive_dns_failures,
                        )
                    raise aiohttp.ClientError(f"DNS failure (no retry): {e}") from e

                if attempt == self.MAX_RETRIES - 1:
                    raise
                delay = min(
                    self.BASE_DELAY * (2**attempt) + random.uniform(0, 1),
                    self.MAX_DELAY,
                )
                logger.warning("Request failed, retrying in %.1fs: %s", delay, e)
                await asyncio.sleep(delay)

        raise aiohttp.ClientError("Max retries exceeded")

    def _convert_to_tonnes(self, troy_ounces: float) -> float:
        """
        Convert troy ounces to tonnes.

        Unit conversion chain:
          troy_oz × TROY_OZ_TO_KG = kg
          kg / KG_TO_TONNES = tonnes
        """
        kg = troy_ounces * self.TROY_OZ_TO_KG
        return kg / self.KG_TO_TONNES

    def _parse_response(self, data: dict, country_code: str) -> list[tuple[str, float]]:
        """
        Parse IMF SDMX response into (period, tonnes) pairs.

        Returns:
            List of (period_str, gold_tonnes) tuples
        """
        result: list[tuple[str, float]] = []

        try:
            data_sets = data.get("data", {}).get("dataSets", [])
            structures = data.get("data", {}).get("structures", [])

            if not data_sets:
                logger.debug(f"No dataSets in response for {country_code}")
                return result

            time_periods: list[str] = []
            for structure in structures:
                dimensions = structure.get("dimensions", {})
                obs_dims = dimensions.get("observation", [])
                for dim in obs_dims:
                    if dim.get("id") == "TIME_PERIOD":
                        time_periods = [v.get("value") for v in dim.get("values", [])]
                        break

            if not time_periods:
                logger.debug(f"No TIME_PERIOD dimension found for {country_code}")
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
                            gold_tonnes = self._convert_to_tonnes(raw_value)

                            period_idx = int(obs_idx)
                            if period_idx < len(time_periods):
                                period_raw = time_periods[period_idx]
                                if "-M" in str(period_raw):
                                    period = period_raw.replace("-M", "-")
                                else:
                                    period = period_raw

                                if gold_tonnes > 0:
                                    result.append((period, round(gold_tonnes, 2)))

                        except (ValueError, TypeError, IndexError):
                            continue

        except Exception as e:
            logger.debug(f"Error parsing IMF response for {country_code}: {e}")

        return result

    async def fetch_gold_reserves(
        self,
        country_code: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> list[GoldReserve]:
        """
        Fetch gold reserves for a country.

        Args:
            country_code: ISO 3-letter country code
            start_period: Start date (YYYY-MM format)
            end_period: End date (YYYY-MM format)

        Returns:
            List of GoldReserve objects
        """
        url = self._build_data_url(country_code, start_period, end_period)

        try:
            data = await self._request_with_backoff(url)
            parsed = self._parse_response(data, country_code)

            country_name = self.country_codes.get(country_code, country_code)

            reserves = []
            for period, tonnes in parsed:
                try:
                    reserves.append(
                        GoldReserve.from_monthly(
                            date_str=period,
                            tonnes=tonnes,
                            country_code=country_code,
                            country_name=country_name,
                            source=SOURCE_IMF,
                        )
                    )
                except ValueError:
                    continue

            return reserves

        except Exception as e:
            logger.error(f"Failed to fetch gold reserves for {country_code}: {e}")
            return []

    async def get_latest_gold_reserve(self, country_code: str) -> GoldReserve | None:
        """Get the most recent gold reserve for a country."""
        end_date = utcnow()
        start_date = end_date - relativedelta(years=1)

        start_period = start_date.strftime(MONTH_FORMAT)
        end_period = end_date.strftime(MONTH_FORMAT)

        reserves = await self.fetch_gold_reserves(country_code, start_period=start_period, end_period=end_period)

        if not reserves:
            return None

        return max(reserves, key=lambda r: r.report_date or utcnow().date())

    async def get_gold_reserves_history(self, country_code: str, years: int = 10) -> list[GoldReserve]:
        """Get historical gold reserves for a country."""
        end_date = utcnow()
        start_date = end_date - relativedelta(years=years)

        start_period = start_date.strftime(MONTH_FORMAT)
        end_period = end_date.strftime(MONTH_FORMAT)

        reserves = await self.fetch_gold_reserves(country_code, start_period=start_period, end_period=end_period)

        logger.debug(f"{country_code}: fetched {len(reserves)} periods")
        return reserves

    async def _precheck_connectivity(self) -> bool:
        """Test DNS connectivity with a single lightweight request.

        Returns True if network is reachable, False if DNS fails.
        Sets circuit breaker on failure to prevent batch spam.
        """
        if self._dns_circuit_open:
            return False

        # Try the first country as a canary request
        first_code = next(iter(self.country_codes), "USA")
        period = utcnow().strftime(MONTH_FORMAT)
        url = self._build_data_url(first_code, start_period=period, end_period=period)

        try:
            await self._request_with_backoff(url)
            return True
        except Exception as e:
            if _is_dns_error(e):
                logger.error("DNS pre-check failed — network unreachable. Skipping batch request. Error: %s", e)
                self._dns_circuit_open = True
                return False
            # Non-DNS errors (rate limit, 500, etc.) — network is fine, proceed
            return True

    async def batch_get_latest_reserves(self, country_codes: list[str] | None = None) -> list[GoldReserve]:
        """Get latest reserves for multiple countries."""
        if country_codes is None:
            country_codes = list(self.country_codes.keys())

        if not await self._precheck_connectivity():
            return []

        tasks = [self.get_latest_gold_reserve(code) for code in country_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: list[GoldReserve] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"Error fetching {country_codes[i]}: {result}")
            elif result:
                valid_results.append(result)

        valid_results.sort(key=lambda r: r.amount_tonnes, reverse=True)
        return valid_results

    async def batch_get_history(
        self, country_codes: list[str] | None = None, years: int = 10
    ) -> list[list[GoldReserve]]:
        """Get historical reserves for multiple countries."""
        if country_codes is None:
            country_codes = list(self.country_codes.keys())

        if not await self._precheck_connectivity():
            return []

        tasks = [self.get_gold_reserves_history(code, years) for code in country_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: list[list[GoldReserve]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"Error fetching history for {country_codes[i]}: {result}")
            elif result:
                valid_results.append(result)

        return valid_results

    async def get_gold_reserves_history_dict(self, country_code: str, years: int = 10) -> dict:
        """Get historical reserves as dict."""
        reserves = await self.get_gold_reserves_history(country_code, years)
        if not reserves:
            return {
                "country_code": country_code,
                "country_name": self.country_codes.get(country_code, country_code),
                "data": {},
            }
        return {
            "country_code": country_code,
            "country_name": reserves[0].country_name if reserves else country_code,
            "data": {r.report_date.strftime(MONTH_FORMAT): r.amount_tonnes for r in reserves if r.report_date},
        }

    async def batch_get_latest_reserves_dict(self, country_codes: list[str] | None = None) -> list[dict]:
        """Get latest reserves as list of dicts."""
        reserves = await self.batch_get_latest_reserves(country_codes)
        return [
            {
                "country_code": r.country_code,
                "country_name": r.country_name,
                "value": r.amount_tonnes,
                "period": r.report_date.strftime(MONTH_FORMAT) if r.report_date else "",
            }
            for r in reserves
        ]

    async def batch_get_history_dict(self, country_codes: list[str] | None = None, years: int = 10) -> list[dict]:
        """Get historical reserves as list of dicts."""
        if country_codes is None:
            country_codes = list(self.country_codes.keys())

        if not await self._precheck_connectivity():
            return []

        tasks = [self.get_gold_reserves_history_dict(code, years) for code in country_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: list[dict] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"Error fetching history for {country_codes[i]}: {result}")
            elif result and result.get("data"):
                valid_results.append(result)

        return valid_results
