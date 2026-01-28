import asyncio
import re
from datetime import datetime
from typing import List

from ..core.models import Asset, Quote
from ..providers.fetcher import fetcher
from ..utils.time_util import normalize_time
from .base import QuoteSource


class EastMoneyFundSource(QuoteSource):
    async def fetch(self, assets: List[Asset]) -> List[Quote]:
        tasks = []
        for asset in assets:
            url = f"http://fundgz.1234567.com.cn/js/{asset.api_code}.js"
            tasks.append(self._fetch_single_fund(asset, url))
        return await asyncio.gather(*tasks)

    async def _fetch_single_fund(self, asset: Asset, url: str) -> Quote:
        quote = None
        try:
            text = await fetcher.fetch(url, text_mode=True)
            match = re.search(r"jsonpgz\((.*)\);", text)
            if match:
                data = match.group(1)
                if data:
                    import json

                    info = json.loads(data)
                    price = float(info.get("gsz", info.get("dwjz", 0)))
                    change = float(info.get("gszzl", 0))
                    time_str = info.get("gztime", info.get("jzrq", ""))

                    if price > 0:
                        quote = Quote(
                            code=asset.code,
                            name=info.get("name", asset.name),
                            price=price,
                            change_percent=change,
                            update_time=normalize_time(time_str),
                            market=asset.market,
                            type=asset.type,
                        )
        except Exception:
            pass

        if quote:
            return quote

        # Fallback to NAV
        return await self._fetch_fund_nav_fallback(asset)

    async def _fetch_fund_nav_fallback(self, asset: Asset) -> Quote:
        url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={asset.code}&pageIndex=1&pageSize=1"
        headers = {"Referer": "http://fundf10.eastmoney.com/"}

        try:
            data = await fetcher.fetch(url, headers=headers)
            if data and "Data" in data and data["Data"] and "LSJZList" in data["Data"]:
                lsjz = data["Data"]["LSJZList"]
                if lsjz and len(lsjz) > 0:
                    latest = lsjz[0]
                    price = float(latest.get("DWJZ", 0))
                    change = float(latest.get("JZZZL", 0))
                    date_str = latest.get("FSRQ", "")

                    return Quote(
                        code=asset.code,
                        name=asset.name,
                        price=price,
                        change_percent=change,
                        update_time=normalize_time(date_str),
                        market=asset.market,
                        type=asset.type,
                    )
        except Exception as e:
            print(f"Fund fallback error for {asset.code}: {e}")
            pass

        return Quote(
            code=asset.code,
            name=asset.name,
            price=0.0,
            change_percent=0.0,
            update_time="-",
            market=asset.market,
            type=asset.type,
        )


class EastMoneyGlobalSource(QuoteSource):
    async def fetch(self, assets: List[Asset]) -> List[Quote]:
        secids = ",".join([a.api_code for a in assets])
        url = "http://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {"secids": secids, "fields": "f2,f3,f12,f14,f59"}

        quotes = []
        try:
            data = await fetcher.fetch(url, params=params)
            if data and "data" in data and data["data"] and "diff" in data["data"]:
                items = data["data"]["diff"]
                if isinstance(items, list):
                    item_list = items
                else:
                    item_list = items.values()

                code_map = {}
                for a in assets:
                    simple_code = a.api_code.split(".")[-1]
                    code_map[simple_code] = a

                for item in item_list:
                    f12 = item.get("f12")
                    if f12 in code_map:
                        asset = code_map[f12]
                        price_raw = item.get("f2", 0)
                        pct_raw = item.get("f3", 0)
                        decimals = item.get("f59") or 2

                        factor = 10**decimals
                        price = price_raw / factor if price_raw != "-" else 0.0
                        change_pct = pct_raw / 100.0 if pct_raw != "-" else 0.0

                        quote = Quote(
                            code=asset.code,
                            name=item.get("f14", asset.name),
                            price=price,
                            change_percent=change_pct,
                            update_time=normalize_time(
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ),
                            market=asset.market,
                            type=asset.type,
                        )
                        quotes.append(quote)
        except Exception as e:
            print(f"EM Global error: {e}")

        return quotes
