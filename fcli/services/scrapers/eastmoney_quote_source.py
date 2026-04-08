"""东方财富行情数据源"""

import asyncio

from ...core.code_mapper import code_mapper
from ...core.config import Settings
from ...core.interfaces.source import QuoteSourceABC
from ...core.models import Asset, Quote
from ...infra.http_client import HttpClient
from ...utils.calc import calc_change_percent
from ...utils.time_util import utcnow


class EastmoneyQuoteSource(QuoteSourceABC):
    """东方财富行情数据源"""

    def __init__(self, http_client: HttpClient, config: Settings):
        self._http_client = http_client
        self._config = config

    @property
    def name(self) -> str:
        return "eastmoney"

    async def is_available(self) -> bool:
        return True

    async def fetch_single(self, asset: Asset) -> Quote | None:
        secid = code_mapper.to_eastmoney_secid(asset.api_code, asset.market)
        if not secid:
            return None

        em = self._config.datasource.eastmoney
        url = em.quote_api_url
        params = {
            "secid": secid,
            "fields": em.SINGLE_FIELDS,
        }

        data = await self._http_client.fetch(url, params=params)

        if not data or not isinstance(data, dict) or data.get("rc") != 0 or not data.get("data"):
            return None

        d = data["data"]
        divisor = em.PRICE_DIVISOR

        price = float(d.get(em.F_SINGLE_PRICE, 0)) / divisor
        prev_close = float(d.get(em.F_SINGLE_PREV_CLOSE, 0)) / divisor

        return Quote(
            code=asset.code,
            name=asset.name,
            price=price,
            change_percent=calc_change_percent(price, prev_close),
            update_time=utcnow(),
            market=asset.market,
            type=asset.type,
            high=float(d.get(em.F_SINGLE_HIGH, 0)) / divisor if d.get(em.F_SINGLE_HIGH) else None,
            low=float(d.get(em.F_SINGLE_LOW, 0)) / divisor if d.get(em.F_SINGLE_LOW) else None,
            volume=float(d.get(em.F_SINGLE_VOLUME, 0))
            if d.get(em.F_SINGLE_VOLUME) and d.get(em.F_SINGLE_VOLUME) != "-"
            else None,
        )

    async def fetch_all(self, assets: list[Asset]) -> list[Quote]:
        results = await asyncio.gather(
            *[self.fetch_single(a) for a in assets],
            return_exceptions=True,
        )
        return [r for r in results if isinstance(r, Quote)]
