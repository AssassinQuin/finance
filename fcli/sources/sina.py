import re
from datetime import datetime
from typing import List

from ..core.models import Asset, AssetType, Market, Quote
from ..providers.fetcher import fetcher
from ..utils.time_util import normalize_time
from .base import QuoteSource


class SinaSource(QuoteSource):
    async def fetch(self, assets: List[Asset]) -> List[Quote]:
        # Max 50 per batch
        batch_size = 50
        quotes = []

        for i in range(0, len(assets), batch_size):
            batch = assets[i : i + batch_size]
            codes = ",".join([a.api_code for a in batch])
            url = f"http://hq.sinajs.cn/list={codes}"

            try:
                text = await fetcher.fetch(url, text_mode=True)
                lines = text.strip().split("\n")

                asset_map = {a.api_code: a for a in batch}

                for line in lines:
                    if not line:
                        continue
                    match = re.search(r'var hq_str_(\w+)="([^"]+)";', line)
                    if match:
                        api_code, data_str = match.groups()
                        if api_code in asset_map:
                            asset = asset_map[api_code]
                            quote = self._parse_sina_data(asset, data_str)
                            if quote:
                                quotes.append(quote)
            except Exception as e:
                print(f"Sina batch error: {e}")

        return quotes

    def _parse_sina_data(self, asset: Asset, data_str: str) -> Quote:
        parts = data_str.split(",")
        if not parts or len(parts) < 3:
            return None

        price = 0.0
        change_pct = 0.0
        update_time = ""
        name = asset.name

        try:
            if asset.market == Market.CN and asset.type != AssetType.INDEX:
                name = parts[0]
                prev_close = float(parts[2])
                price = float(parts[3])
                if prev_close > 0:
                    change_pct = ((price - prev_close) / prev_close) * 100
                update_time = f"{parts[30]} {parts[31]}"

            elif asset.market == Market.CN and asset.type == AssetType.INDEX:
                if len(parts) > 10:
                    name = parts[0]
                    prev_close = float(parts[2])
                    price = float(parts[3])
                    if prev_close > 0:
                        change_pct = ((price - prev_close) / prev_close) * 100
                    update_time = (
                        f"{parts[30]} {parts[31]}"
                        if len(parts) > 31
                        else datetime.now().strftime("%H:%M:%S")
                    )
                else:
                    name = parts[0]
                    price = float(parts[1])
                    change_pct = float(parts[3])
                    update_time = datetime.now().strftime("%H:%M:%S")

            elif asset.market == Market.US:
                name = parts[0]
                price = float(parts[1])
                change_pct = float(parts[2])
                update_time = parts[3]

            elif asset.market == Market.HK:
                name = parts[1]
                price = float(parts[6])
                change_pct = float(parts[8])
                update_time = f"{parts[17]} {parts[18]}"

        except (ValueError, IndexError):
            pass

        return Quote(
            code=asset.code,
            name=name,
            price=price,
            change_percent=change_pct,
            update_time=normalize_time(update_time),
            market=asset.market,
            type=asset.type,
        )
