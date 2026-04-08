"""东方财富行情数据源"""

from ...core.code_mapper import code_mapper
from ...core.config import Settings
from ...core.interfaces.source import QuoteSourceABC
from ...core.models import Asset, Quote
from ...infra.http_client import HttpClient
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

        url = self._config.datasource.eastmoney.quote_api_url
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f107,f162,f163,f166,f169,f170,f171,f184",
        }

        data = await self._http_client.fetch(url, params=params)

        if not data or not isinstance(data, dict) or data.get("rc") != 0 or not data.get("data"):
            return None

        d = data["data"]

        price = float(d.get("f43", 0)) / 100
        prev_close = float(d.get("f60", 0)) / 100

        change_percent = 0.0
        if prev_close > 0:
            change_percent = (price - prev_close) / prev_close * 100

        return Quote(
            code=asset.code,
            name=asset.name,
            price=price,
            change_percent=change_percent,
            update_time=utcnow(),
            market=asset.market,
            type=asset.type,
            high=float(d.get("f44", 0)) / 100 if d.get("f44") else None,
            low=float(d.get("f45", 0)) / 100 if d.get("f45") else None,
            volume=float(d.get("f47", 0)) if d.get("f47") and d.get("f47") != "-" else None,
        )

    async def fetch_all(self, assets: list[Asset]) -> list[Quote]:
        import asyncio

        results = await asyncio.gather(
            *[self.fetch_single(a) for a in assets],
            return_exceptions=True,
        )
        return [r for r in results if isinstance(r, Quote)]
