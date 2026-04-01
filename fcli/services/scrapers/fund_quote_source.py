"""基金行情数据源 (fundgz.1234567.com.cn)"""

import json
import re
from datetime import datetime
from typing import Any

from ...core.config import Settings
from ...core.interfaces.source import QuoteSourceABC
from ...core.models import Asset, Market, Quote
from ...infra.http_client import HttpClient
from ...utils.logger import quote_logger as logger
from ...utils.time_util import utcnow


class FundQuoteSource(QuoteSourceABC):
    """基金行情数据源"""

    def __init__(self, http_client: HttpClient, config: Settings):
        self._http_client = http_client
        self._config = config

    @property
    def name(self) -> str:
        return "fund_1234567"

    @property
    def priority(self) -> int:
        return 100

    @property
    def supported_markets(self) -> list[Market]:
        return [Market.CN]

    async def is_available(self) -> bool:
        return True

    async def fetch_single(self, asset: Asset) -> Quote | None:
        quotes = await self.fetch_all([asset])
        return quotes[0] if quotes else None

    async def fetch_all(self, assets: list[Asset]) -> list[Quote]:
        import asyncio

        quotes = await asyncio.gather(*[self._fetch_fund(asset) for asset in assets])
        return [q for q in quotes if q is not None]

    async def _fetch_fund(self, asset: Asset) -> Quote | None:
        if not self._config.datasource.fund.gz_api_url:
            return None
        url = self._config.datasource.fund.gz_api_url.format(code=asset.code)

        text = await self._try_fetch_with_fallback_encodings(url)

        if not text or "jsonpgz" not in text:
            return None

        match = re.search(r"jsonpgz\((.*?)\);", text)
        if not match:
            return None

        try:
            json_str = match.group(1)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                data = self._parse_fund_response(json_str)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.debug(f"Failed to parse fund gz data: {e}")
            return None

        if not data or not data.get("gsz"):
            return None

        price = float(data.get("gsz", 0))
        change_percent = float(data.get("gszzl", 0))

        return Quote(
            code=asset.code,
            name=data.get("name", asset.name),
            price=price,
            change_percent=change_percent,
            update_time=utcnow(),
            market=asset.market,
            type=asset.type,
        )

    async def _try_fetch_with_fallback_encodings(self, url: str) -> str | None:
        for encoding in ["utf-8", "gbk"]:
            try:
                text = await self._http_client.fetch(url, text_mode=True, encoding=encoding)
                if text and "jsonpgz" in text:
                    return text
            except (UnicodeDecodeError, Exception):
                continue
        return None

    def _parse_fund_response(self, json_str: str) -> dict[str, Any]:
        patterns = {
            "fundcode": r'fundcode:"([^"]+)"',
            "name": r'name:"([^"]+)"',
            "gsz": r'gsz:"([^"]+)"',
            "gszzl": r'gszzl:"([^"]+)"',
            "gztime": r'gztime:"([^"]+)"',
        }
        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, json_str)
            if match:
                result[key] = match.group(1)
        return result
