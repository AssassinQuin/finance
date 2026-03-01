from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import json
from ..utils.logger import quote_logger as logger, LogContext
from ..core.cache import cache
from ..core.config import config
from ..core.models import Asset, Quote, Market, AssetType
from ..infra.http_client import http_client
from ..utils.time_util import is_trading_hours, get_cache_ttl


class QuoteService:
    async def fetch_single(self, asset: Asset) -> Optional[Quote]:
        cache_key = f"quote:{asset.code}"
        cached = await cache.async_get(cache_key)

        if cached:
            in_trading = is_trading_hours(asset.market)
            if in_trading:
                logger.debug(
                    "Cache hit (trading hours)",
                    LogContext(operation="cache_lookup", code=asset.code, market=asset.market.value, cache_hit=True),
                )
                return Quote(**cached)
            else:
                logger.debug(
                    "Cache hit (non-trading hours)",
                    LogContext(operation="cache_lookup", code=asset.code, market=asset.market.value, cache_hit=True),
                )
                return Quote(**cached)

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
                    ttl = get_cache_ttl(asset.market)
                    await cache.async_set(cache_key, self._quote_to_dict(quote), ttl)
                    logger.info(
                        "Quote fetched",
                        LogContext(
                            operation="fetch_quote",
                            code=asset.code,
                            market=asset.market.value,
                            source=source,
                            cache_hit=False,
                        ),
                    )
                    return quote
            except Exception as e:
                logger.warning(f"Source {source} failed: {e}")
                if not config.source.fallback_enabled:
                    raise
                continue

        return None

    def _quote_to_dict(self, quote: Quote) -> dict:
        """将 Quote 对象转换为字典用于缓存"""
        return {
            "code": quote.code,
            "name": quote.name,
            "price": quote.price,
            "change_percent": quote.change_percent,
            "update_time": quote.update_time.isoformat()
            if isinstance(quote.update_time, datetime)
            else quote.update_time,
            "market": quote.market.value if hasattr(quote.market, "value") else quote.market,
            "type": quote.type.value if hasattr(quote.type, "value") else quote.type,
            "high": quote.high,
            "low": quote.low,
            "volume": quote.volume,
        }

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
            # 使用 json.loads 替代 eval() 避免安全风险
            # fundgz.1234567 返回的格式是类 JSON 但键未加引号
            json_str = match.group(1)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # 如果失败，使用正则提取关键字段
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
            update_time=datetime.now(),
            market=asset.market,
            type=asset.type,
        )

    def _parse_fund_response(self, json_str: str) -> Dict[str, Any]:
        """
        解析 fundgz.1234567.com.cn 返回的非标准 JSON 格式。
        该 API 返回的格式类似于: {fundcode:"000001",name:"华夏成长",gsz:"1.234",...}
        键没有引号，无法直接用 json.loads 解析。
        """
        # 使用正则提取关键字段
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
            update_time=datetime.now(),
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
            update_time=datetime.now(),
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
            update_time=datetime.now(),
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
            update_time=datetime.now(),
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

        if not data or not isinstance(data, dict) or data.get("rc") != 0 or not data.get("data"):
            return None
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
            update_time=datetime.now(),
            market=asset.market,
            type=asset.type,
            high=float(d.get("f44", 0)) / 100 if d.get("f44") else None,
            low=float(d.get("f45", 0)) / 100 if d.get("f45") else None,
            volume=str(int(d.get("f47", 0))) if d.get("f47") and d.get("f47") != "-" else None,
        )

    async def _fetch_yahoo(self, asset: Asset) -> Optional[Quote]:
        return None

    async def fetch_all(self, assets: List[Asset]) -> List[Quote]:
        """批量获取行情数据，使用批量API优化性能"""
        import asyncio

        quotes = []
        remaining_assets = []

        for asset in assets:
            cache_key = f"quote:{asset.code}"
            cached = cache.get(cache_key)
            if cached:
                in_trading = is_trading_hours(asset.market)
                if in_trading:
                    logger.debug(
                        "Cache hit (trading hours)",
                        LogContext(
                            operation="cache_lookup", code=asset.code, market=asset.market.value, cache_hit=True
                        ),
                    )
                quotes.append(Quote(**cached))
            else:
                remaining_assets.append(asset)

        if not remaining_assets:
            return quotes

        # 按市场分组
        market_groups = {
            Market.GLOBAL: [],
            Market.CN: [],
            Market.HK: [],
            Market.US: [],
        }
        other_assets = []

        for asset in remaining_assets:
            if asset.type == AssetType.FUND:
                other_assets.append(asset)  # 基金走单独逻辑
            elif asset.market in market_groups:
                market_groups[asset.market].append(asset)
            else:
                other_assets.append(asset)

        # 并行获取各市场数据
        tasks = []

        # 全球指数 - 东方财富批量 API
        if market_groups[Market.GLOBAL]:
            secids = [
                f"100.{asset.api_code.split('.')[1] if '.' in asset.api_code else asset.api_code}"
                for asset in market_groups[Market.GLOBAL]
            ]
            tasks.append(self._fetch_global_batch(market_groups[Market.GLOBAL], secids))

        # A股 - 新浪批量 API
        if market_groups[Market.CN]:
            tasks.append(self._fetch_sina_batch(market_groups[Market.CN], Market.CN))

        # 港股 - 新浪批量 API
        if market_groups[Market.HK]:
            tasks.append(self._fetch_sina_batch(market_groups[Market.HK], Market.HK))

        # 美股 - 新浪批量 API
        if market_groups[Market.US]:
            tasks.append(self._fetch_sina_batch(market_groups[Market.US], Market.US))

        # 其他资产 - 单条并发
        if other_assets:
            tasks.append(self._fetch_others_batch(other_assets))

        # 并行执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                quotes.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Batch fetch failed: {result}")

        return quotes

    async def _fetch_sina_batch(self, assets: List[Asset], market: Market) -> List[Quote]:
        """批量获取新浪行情数据 (支持 A股/港股/美股)"""
        if not assets:
            return []

        # 构建批量请求 URL
        codes = [asset.api_code for asset in assets]
        url = f"https://hq.sinajs.cn/list={','.join(codes)}"

        try:
            text = await http_client.fetch(url, text_mode=True)
            if not text:
                return []

            # 解析返回数据
            quotes = []
            asset_map = {asset.api_code: asset for asset in assets}

            # 新浪返回格式: var hq_str_sh600519="...";
            for line in text.strip().split("\n"):
                if "=" not in line:
                    continue

                # 提取代码和数据
                code_part, data_part = line.split("=", 1)
                api_code = code_part.split("_")[-1]

                if api_code not in asset_map:
                    continue

                asset = asset_map[api_code]
                data_str = data_part.strip('";\n')

                if not data_str:
                    continue

                # 根据市场类型解析
                quote = self._parse_sina_data(asset, data_str, market)
                if quote:
                    quotes.append(quote)
                    cache_key = f"quote:{asset.code}"
                    ttl = get_cache_ttl(asset.market)
                    await cache.async_set(cache_key, self._quote_to_dict(quote), ttl)

            return quotes

        except Exception as e:
            logger.error(f"Sina batch fetch failed for {market}: {e}")
            return []

    def _parse_sina_data(self, asset: Asset, data_str: str, market: Market) -> Optional[Quote]:
        """统一解析新浪返回数据"""
        parts = data_str.split(",")

        if market == Market.CN:
            # A股格式: 名称,今开,昨收,当前,最高,最低,...
            if len(parts) < 32:
                return None
            return Quote(
                code=asset.code,
                name=parts[0] or asset.name,
                price=float(parts[3]) if parts[3] else 0.0,
                change_percent=self._calc_change_percent(
                    float(parts[3]) if parts[3] else 0, float(parts[2]) if parts[2] else 0
                ),
                update_time=datetime.now(),
                market=asset.market,
                type=asset.type,
                high=float(parts[4]) if parts[4] else None,
                low=float(parts[5]) if parts[5] else None,
                volume=parts[8] if parts[8] else None,
            )

        elif market == Market.HK:
            # 港股格式: ,名称,英文名,昨收,今开,最高,当前,...
            if len(parts) < 15:
                return None
            return Quote(
                code=asset.code,
                name=parts[1] or asset.name,
                price=float(parts[6]) if parts[6] else 0.0,
                change_percent=self._calc_change_percent(
                    float(parts[6]) if parts[6] else 0, float(parts[3]) if parts[3] else 0
                ),
                update_time=datetime.now(),
                market=asset.market,
                type=asset.type,
                high=float(parts[4]) if parts[4] else None,
                low=float(parts[5]) if parts[5] else None,
                volume=parts[12] if parts[12] else None,
            )

        elif market == Market.US:
            # 美股格式: 名称,当前,涨跌,涨跌幅,...
            if len(parts) < 15:
                return None
            return Quote(
                code=asset.code,
                name=parts[0] or asset.name,
                price=float(parts[1]) if parts[1] else 0.0,
                change_percent=self._calc_change_percent(
                    float(parts[1]) if parts[1] else 0, float(parts[26]) if parts[26] else 0
                ),
                update_time=datetime.now(),
                market=asset.market,
                type=asset.type,
                high=float(parts[4]) if parts[4] else None,
                low=float(parts[5]) if parts[5] else None,
                volume=parts[10] if parts[10] else None,
            )

        return None

    def _calc_change_percent(self, price: float, prev_close: float) -> float:
        """计算涨跌幅"""
        if prev_close > 0:
            return (price - prev_close) / prev_close * 100
        return 0.0

    async def _fetch_others_batch(self, assets: List[Asset]) -> List[Quote]:
        """获取其他类型资产 (单条并发)"""
        import asyncio

        tasks = [self.fetch_single(asset) for asset in assets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, Quote)]

    async def _fetch_global_batch(self, assets: List[Asset], secids: List[str]) -> List[Quote]:
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

        if not data or not isinstance(data, dict) or data.get("rc") != 0 or not data.get("data"):
            return []
            return []

        quotes = []
        asset_map = {
            asset.api_code.split(".")[1] if "." in asset.api_code else asset.api_code: asset for asset in assets
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
                    update_time=datetime.now(),
                    market=asset.market,
                    type=asset.type,
                    high=float(item.get("f17", 0)) if item.get("f17") else None,
                    low=float(item.get("f18", 0)) if item.get("f18") else None,
                    volume=str(int(float(item.get("f47", 0)))) if item.get("f47") and item.get("f47") != "-" else None,
                )
            )

            cache_key = f"quote:{asset.code}"
            ttl = get_cache_ttl(asset.market)
            await cache.async_set(cache_key, self._quote_to_dict(quotes[-1]), ttl)

        return quotes


quote_service = QuoteService()
