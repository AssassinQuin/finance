from typing import List, Optional, Dict, Any
from datetime import datetime
import re
from ..core.models import Quote, Asset, Market, AssetType
from ..core.config import config
from ..core.cache import cache
from ..infra.http_client import http_client


class QuoteService:
    async def fetch_single(self, asset: Asset) -> Optional[Quote]:
        for source in config.source.quote_priority:
            try:
                if source == "sina":
                    quote = await self._fetch_sina(asset)
                elif source == "eastmoney":
                    quote = await self._fetch_eastmoney(asset)
                elif source == "yahoo":
                    quote = await self._fetch_yahoo(asset)
                else:
                    continue

                if quote:
                    return quote
            except Exception as e:
                if not config.source.fallback_enabled:
                    raise
                continue

        return None

    async def _fetch_sina(self, asset: Asset) -> Optional[Quote]:
        if asset.type == AssetType.FUND:
            return await self._fetch_fund_1234567(asset)
        elif asset.market == Market.CN:
            return await self._fetch_sina_cn(asset)
        elif asset.market == Market.HK:
            return await self._fetch_sina_hk(asset)
        elif asset.market == Market.US:
            return await self._fetch_sina_us(asset)
        elif asset.market == Market.GLOBAL:
            return await self._fetch_sina_global(asset)
        return None

    async def _fetch_fund_1234567(self, asset: Asset) -> Optional[Quote]:
        url = f"https://fundgz.1234567.com.cn/js/{asset.api_code}.js"
        text = await http_client.fetch(url, text_mode=True)

        if not text or "jsonpgz" not in text:
            return None

        match = re.search(r"jsonpgz\((.*?)\);", text)
        if not match:
            return None

        try:
            data = eval(match.group(1))
        except:
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
            update_time=data.get("gztime", "")[-8:]
            if data.get("gztime")
            else datetime.now().strftime("%H:%M:%S"),
            market=asset.market,
            type=asset.type,
        )

    async def _fetch_sina_cn(self, asset: Asset) -> Optional[Quote]:
        code = asset.api_code
        url = f"https://hq.sinajs.cn/list={code}"
        text = await http_client.fetch(url, text_mode=True)

        if not text or "=" not in text:
            return None

        data_str = text.split("=")[1].strip('";\n')
        parts = data_str.split(",")

        if len(parts) < 32:
            return None

        name = parts[0]
        price = float(parts[3]) if parts[3] else 0.0
        prev_close = float(parts[2]) if parts[2] else 0.0

        change_percent = 0.0
        if prev_close > 0:
            change_percent = (price - prev_close) / prev_close * 100

        return Quote(
            code=asset.code,
            name=name or asset.name,
            price=price,
            change_percent=change_percent,
            update_time=datetime.now().strftime("%H:%M:%S"),
            market=asset.market,
            type=asset.type,
            high=float(parts[4]) if parts[4] else None,
            low=float(parts[5]) if parts[5] else None,
            volume=parts[8] if parts[8] else None,
        )

    async def _fetch_sina_hk(self, asset: Asset) -> Optional[Quote]:
        code = asset.api_code
        url = f"https://hq.sinajs.cn/list={code}"
        text = await http_client.fetch(url, text_mode=True)

        if not text or "=" not in text:
            return None

        data_str = text.split("=")[1].strip('";\n')
        parts = data_str.split(",")

        if len(parts) < 15:
            return None

        name = parts[1]
        price = float(parts[6]) if parts[6] else 0.0
        prev_close = float(parts[3]) if parts[3] else 0.0

        change_percent = 0.0
        if prev_close > 0:
            change_percent = (price - prev_close) / prev_close * 100

        return Quote(
            code=asset.code,
            name=name or asset.name,
            price=price,
            change_percent=change_percent,
            update_time=datetime.now().strftime("%H:%M:%S"),
            market=asset.market,
            type=asset.type,
            high=float(parts[4]) if parts[4] else None,
            low=float(parts[5]) if parts[5] else None,
            volume=parts[12] if parts[12] else None,
        )

    async def _fetch_sina_us(self, asset: Asset) -> Optional[Quote]:
        code = asset.api_code
        url = f"https://hq.sinajs.cn/list={code}"
        text = await http_client.fetch(url, text_mode=True)

        if not text or "=" not in text:
            return None

        data_str = text.split("=")[1].strip('";\n')
        parts = data_str.split(",")

        if len(parts) < 15:
            return None

        name = parts[0]
        price = float(parts[1]) if parts[1] else 0.0
        prev_close = float(parts[26]) if parts[26] else 0.0

        change_percent = 0.0
        if prev_close > 0:
            change_percent = (price - prev_close) / prev_close * 100

        return Quote(
            code=asset.code,
            name=name or asset.name,
            price=price,
            change_percent=change_percent,
            update_time=datetime.now().strftime("%H:%M:%S"),
            market=asset.market,
            type=asset.type,
            high=float(parts[4]) if parts[4] else None,
            low=float(parts[5]) if parts[5] else None,
            volume=parts[10] if parts[10] else None,
        )

    async def _fetch_sina_global(self, asset: Asset) -> Optional[Quote]:
        code = asset.api_code
        url = f"https://hq.sinajs.cn/list={code}"
        text = await http_client.fetch(url, text_mode=True)

        if not text or "=" not in text:
            return None

        data_str = text.split("=")[1].strip('";\n')
        parts = data_str.split(",")

        if len(parts) < 3:
            return None

        name = parts[0]
        price = float(parts[1]) if parts[1] else 0.0
        prev_close = float(parts[2]) if parts[2] else 0.0

        change_percent = 0.0
        if prev_close > 0:
            change_percent = (price - prev_close) / prev_close * 100

        return Quote(
            code=asset.code,
            name=name or asset.name,
            price=price,
            change_percent=change_percent,
            update_time=datetime.now().strftime("%H:%M:%S"),
            market=asset.market,
            type=asset.type,
        )

    async def _fetch_eastmoney(self, asset: Asset) -> Optional[Quote]:
        secid_map = {
            Market.CN: f"1.{asset.api_code[2:]}"
            if asset.api_code.startswith(("sh", "SH"))
            else f"0.{asset.api_code[2:]}",
            Market.HK: f"116.{asset.api_code.replace('rt_hk', '')}",
            Market.US: f"105.{asset.api_code}",
            Market.GLOBAL: f"106.{asset.api_code.split('.')[1] if '.' in asset.api_code else asset.api_code}",
        }

        secid = secid_map.get(asset.market)
        if not secid:
            return None

        url = f"https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f107,f162,f163,f166,f169,f170,f171,f184",
        }

        data = await http_client.fetch(url, params=params)

        if not data or data.get("rc") != 0 or not data.get("data"):
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
            update_time=datetime.now().strftime("%H:%M:%S"),
            market=asset.market,
            type=asset.type,
            high=float(d.get("f44", 0)) / 100 if d.get("f44") else None,
            low=float(d.get("f45", 0)) / 100 if d.get("f45") else None,
            volume=str(int(d.get("f47", 0)))
            if d.get("f47") and d.get("f47") != "-"
            else None,
        )

    async def _fetch_yahoo(self, asset: Asset) -> Optional[Quote]:
        return None

    async def fetch_all(self, assets: List[Asset]) -> List[Quote]:
        import asyncio

        global_assets = [a for a in assets if a.market == Market.GLOBAL]
        cn_assets = [a for a in assets if a.market == Market.CN]
        hk_assets = [a for a in assets if a.market == Market.HK]
        other_assets = [
            a for a in assets if a.market not in [Market.GLOBAL, Market.CN, Market.HK]
        ]

        quotes = []

        if global_assets:
            secids = [
                f"100.{asset.api_code.split('.')[1] if '.' in asset.api_code else asset.api_code}"
                for asset in global_assets
            ]
            quotes.extend(await self._fetch_global_batch(global_assets, secids))

        if cn_assets:
            tasks = [self.fetch_single(asset) for asset in cn_assets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for asset, result in zip(cn_assets, results):
                if isinstance(result, Quote):
                    quotes.append(result)

        if hk_assets:
            tasks = [self.fetch_single(asset) for asset in hk_assets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for asset, result in zip(hk_assets, results):
                if isinstance(result, Quote):
                    quotes.append(result)

        if other_assets:
            tasks = [self.fetch_single(asset) for asset in other_assets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for asset, result in zip(other_assets, results):
                if isinstance(result, Quote):
                    quotes.append(result)

        return quotes

    async def _fetch_global_batch(
        self, assets: List[Asset], secids: List[str]
    ) -> List[Quote]:
        if not secids:
            return []

        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": 2,
            "invt": 2,
            "secids": ",".join(secids),
            "fields": "f1,f2,f3,f4,f12,f14,f15,f16,f17,f18,f43,f47,f48",
        }

        data = await http_client.fetch(url, params=params)

        if not data or data.get("rc") != 0 or not data.get("data"):
            return []

        quotes = []
        asset_map = {
            asset.api_code.split(".")[1]
            if "." in asset.api_code
            else asset.api_code: asset
            for asset in assets
        }

        for item in data["data"].get("diff", []):
            code = item.get("f12")
            if not code or code not in asset_map:
                continue

            asset = asset_map[code]
            price = float(item.get("f2", 0)) if item.get("f2") else 0.0
            change_percent = float(item.get("f3", 0)) if item.get("f3") else 0.0

            quotes.append(
                Quote(
                    code=asset.code,
                    name=item.get("f14", asset.name),
                    price=price,
                    change_percent=change_percent,
                    update_time=datetime.now().strftime("%H:%M:%S"),
                    market=asset.market,
                    type=asset.type,
                    high=float(item.get("f17", 0)) if item.get("f17") else None,
                    low=float(item.get("f18", 0)) if item.get("f18") else None,
                    volume=str(int(float(item.get("f47", 0))))
                    if item.get("f47") and item.get("f47") != "-"
                    else None,
                )
            )

        return quotes


quote_service = QuoteService()
