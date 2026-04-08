"""新浪行情数据源"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.models import Asset, Market, Quote

from ...core.config import Settings
from ...core.interfaces.source import QuoteSourceABC
from ...core.models.base import Market
from ...infra.http_client import HttpClient
from ...utils.calc import calc_change_percent
from ...utils.logger import quote_logger as logger
from ...utils.time_util import utcnow


@dataclass(frozen=True)
class SinaFieldMap:
    name: int
    price: int
    prev_close: int
    high: int
    low: int
    volume: int
    min_parts: int


SINA_FIELD_MAPS: dict[Market, SinaFieldMap] = {
    Market.CN: SinaFieldMap(name=0, price=3, prev_close=2, high=4, low=5, volume=8, min_parts=32),
    Market.HK: SinaFieldMap(name=1, price=6, prev_close=3, high=4, low=5, volume=12, min_parts=15),
    Market.US: SinaFieldMap(name=0, price=1, prev_close=26, high=4, low=5, volume=10, min_parts=15),
}


class SinaQuoteSource(QuoteSourceABC):
    """新浪行情数据源"""

    def __init__(self, http_client: HttpClient, config: Settings):
        self._http_client = http_client
        self._config = config

    @property
    def name(self) -> str:
        return "sina"

    async def is_available(self) -> bool:
        return True

    async def fetch_single(self, asset: Asset) -> Quote | None:
        quotes = await self.fetch_all([asset])
        return quotes[0] if quotes else None

    async def fetch_all(self, assets: list[Asset]) -> list[Quote]:
        if not assets:
            return []

        market_assets: dict[Market, list[Asset]] = {}
        for asset in assets:
            if asset.market not in market_assets:
                market_assets[asset.market] = []
            market_assets[asset.market].append(asset)

        all_quotes = []
        for market, market_asset_list in market_assets.items():
            quotes = await self._fetch_batch(market_asset_list, market)
            all_quotes.extend(quotes)

        return all_quotes

    async def _fetch_batch(self, assets: list[Asset], market: Market) -> list[Quote]:
        if not assets:
            return []

        codes = [asset.api_code for asset in assets]
        url = self._config.datasource.sina.cn_quote_url.format(code=",".join(codes))

        try:
            text = await self._http_client.fetch(
                url, text_mode=True, headers={"Referer": self._config.datasource.sina.referer}
            )
            if not text:
                return []

            quotes = []
            asset_map = {asset.api_code: asset for asset in assets}

            for line in text.strip().split("\n"):
                if "=" not in line:
                    continue

                code_part, data_part = line.split("=", 1)
                api_code = code_part.split("hq_str_")[-1] if "hq_str_" in code_part else code_part.split("_")[-1]

                if api_code not in asset_map:
                    continue

                asset = asset_map[api_code]
                data_str = data_part.strip('";\n')

                if not data_str:
                    continue

                quote = self._parse_data(asset, data_str, market)
                if quote:
                    quotes.append(quote)

            return quotes

        except Exception as e:
            logger.error(f"Sina batch fetch failed for {market}: {e}")
            return []

    def _parse_data(self, asset: Asset, data_str: str, market: Market) -> Quote | None:
        from ...core.models import Quote

        fm = SINA_FIELD_MAPS.get(market)
        if fm is None:
            return None

        parts = data_str.split(",")
        if len(parts) < fm.min_parts:
            return None

        price = float(parts[fm.price]) if parts[fm.price] else 0.0
        prev_close = float(parts[fm.prev_close]) if parts[fm.prev_close] else 0.0

        return Quote(
            code=asset.code,
            name=parts[fm.name] or asset.name,
            price=price,
            change_percent=calc_change_percent(price, prev_close),
            update_time=utcnow(),
            market=asset.market,
            type=asset.type,
            high=float(parts[fm.high]) if parts[fm.high] else None,
            low=float(parts[fm.low]) if parts[fm.low] else None,
            volume=parts[fm.volume] if parts[fm.volume] else None,
        )
