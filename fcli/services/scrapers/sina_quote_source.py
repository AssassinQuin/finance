"""新浪行情数据源"""

from ...core.config import Settings
from ...core.interfaces.source import QuoteSourceABC
from ...core.models import Asset, Market, Quote
from ...infra.http_client import HttpClient
from ...utils.logger import quote_logger as logger
from ...utils.time_util import utcnow


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
        url = f"https://hq.sinajs.cn/list={','.join(codes)}"

        try:
            text = await self._http_client.fetch(
                url, text_mode=True, headers={"Referer": "https://finance.sina.com.cn"}
            )
            if not text:
                return []

            quotes = []
            asset_map = {asset.api_code: asset for asset in assets}

            for line in text.strip().split("\n"):
                if "=" not in line:
                    continue

                code_part, data_part = line.split("=", 1)
                api_code = code_part.split("_")[-1]

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
        parts = data_str.split(",")

        if market == Market.CN:
            if len(parts) < 32:
                return None
            return Quote(
                code=asset.code,
                name=parts[0] or asset.name,
                price=float(parts[3]) if parts[3] else 0.0,
                change_percent=self._calc_change_percent(
                    float(parts[3]) if parts[3] else 0, float(parts[2]) if parts[2] else 0
                ),
                update_time=utcnow(),
                market=asset.market,
                type=asset.type,
                high=float(parts[4]) if parts[4] else None,
                low=float(parts[5]) if parts[5] else None,
                volume=float(parts[8]) if parts[8] else None,
            )

        elif market == Market.HK:
            if len(parts) < 15:
                return None
            return Quote(
                code=asset.code,
                name=parts[1] or asset.name,
                price=float(parts[6]) if parts[6] else 0.0,
                change_percent=self._calc_change_percent(
                    float(parts[6]) if parts[6] else 0, float(parts[3]) if parts[3] else 0
                ),
                update_time=utcnow(),
                market=asset.market,
                type=asset.type,
                high=float(parts[4]) if parts[4] else None,
                low=float(parts[5]) if parts[5] else None,
                volume=parts[12] if parts[12] else None,
            )

        elif market == Market.US:
            if len(parts) < 15:
                return None
            return Quote(
                code=asset.code,
                name=parts[0] or asset.name,
                price=float(parts[1]) if parts[1] else 0.0,
                change_percent=self._calc_change_percent(
                    float(parts[1]) if parts[1] else 0, float(parts[26]) if parts[26] else 0
                ),
                update_time=utcnow(),
                market=asset.market,
                type=asset.type,
                high=float(parts[4]) if parts[4] else None,
                low=float(parts[5]) if parts[5] else None,
                volume=float(parts[10]) if parts[10] else None,
            )

        return None

    def _calc_change_percent(self, price: float, prev_close: float) -> float:
        if prev_close > 0:
            return (price - prev_close) / prev_close * 100
        return 0.0
