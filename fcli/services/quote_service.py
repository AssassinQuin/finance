"""Quote Service - 行情查询服务

重构说明:
- 使用依赖注入模式，通过构造函数传入依赖
- 移除全局实例导入，提高可测试性
- 通过 sources 注入数据源，实现策略模式
"""

import json
import re
from datetime import datetime
from typing import Any

from ..core.cache_strategy import ICacheStrategy
from ..core.config import Settings
from ..core.interfaces.cache import ICache
from ..core.interfaces.source import IQuoteSource
from ..core.models import Asset, AssetType, Market, Quote
from ..core.stores.quote_fact import QuoteFactStore
from ..infra.http_client import HttpClient
from ..utils.logger import LogContext
from ..utils.logger import quote_logger as logger
from ..utils.time_util import is_trading_hours


class QuoteService:
    """行情查询服务

    通过依赖注入接收 cache, config, http_client 等基础设施，
    以及数据源列表 sources，实现解耦和策略模式。

    Args:
        cache: 缓存实例 (ICache)
        config: 配置实例 (Settings)
        http_client: HTTP 客户端实例 (HttpClient)
        cache_strategy: 缓存策略实例 (ICacheStrategy)
        sources: 数据源列表 (List[IQuoteSource])
    """

    def __init__(
        self,
        cache: ICache,
        config: Settings,
        http_client: HttpClient,
        cache_strategy: ICacheStrategy,
        sources: list[IQuoteSource] | None = None,
        fund_source: IQuoteSource | None = None,
    ):
        self._cache = cache
        self._config = config
        self._http_client = http_client
        self._cache_strategy = cache_strategy
        self._sources = sources or []
        self._fund_source = fund_source

    async def fetch_single(self, asset: Asset) -> Quote | None:
        cache_key = f"quote:{asset.code}"
        cached = await self._cache.async_get(cache_key)

        if cached:
            in_trading = is_trading_hours(asset.market)
            if in_trading:
                logger.debug(
                    "Cache hit (trading hours)",
                    LogContext(operation="cache_lookup", code=asset.code, market=asset.market.value, cache_hit=True),
                )
            else:
                logger.debug(
                    "Cache hit (non-trading hours)",
                    LogContext(operation="cache_lookup", code=asset.code, market=asset.market.value, cache_hit=True),
                )
            return Quote(**cached)

        for source in self._config.datasource.quote_priority:
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
                    ttl = self._cache_strategy.get_ttl(asset.type, asset.market)
                    await self._cache.async_set(cache_key, self._quote_to_dict(quote), ttl)
                    await QuoteFactStore.save(quote)
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
                if not self._config.datasource.fallback_enabled:
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

    async def _fetch_sina(self, asset: Asset) -> Quote | None:
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

    async def _fetch_fund_1234567(self, asset: Asset) -> Quote | None:
        # 使用配置化的URL
        url = self._config.datasource.fund.gz_api_url.format(code=asset.api_code)
        text = await self._http_client.fetch(url, text_mode=True)

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

    def _parse_fund_response(self, json_str: str) -> dict[str, Any]:
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

    async def _fetch_sina_cn(self, asset: Asset) -> Quote | None:
        code = asset.api_code
        # 使用配置化的URL
        url = self._config.datasource.sina.cn_quote_url.format(code=code)
        text = await self._http_client.fetch(url, text_mode=True)

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

    async def _fetch_sina_hk(self, asset: Asset) -> Quote | None:
        code = asset.api_code
        # 使用配置化的URL
        url = self._config.datasource.sina.cn_quote_url.format(code=code)
        text = await self._http_client.fetch(url, text_mode=True)

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

    async def _fetch_sina_us(self, asset: Asset) -> Quote | None:
        code = asset.api_code
        # 使用配置化的URL
        url = self._config.datasource.sina.cn_quote_url.format(code=code)
        text = await self._http_client.fetch(url, text_mode=True)

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

    async def _fetch_sina_global(self, asset: Asset) -> Quote | None:
        code = asset.api_code
        # 使用配置化的URL
        url = self._config.datasource.sina.cn_quote_url.format(code=code)
        text = await self._http_client.fetch(url, text_mode=True)

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

    async def _fetch_eastmoney(self, asset: Asset) -> Quote | None:
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
            update_time=datetime.now(),
            market=asset.market,
            type=asset.type,
            high=float(d.get("f44", 0)) / 100 if d.get("f44") else None,
            low=float(d.get("f45", 0)) / 100 if d.get("f45") else None,
            volume=str(int(d.get("f47", 0))) if d.get("f47") and d.get("f47") != "-" else None,
        )

    async def _fetch_yahoo(self, asset: Asset) -> Quote | None:
        return None

    async def fetch_all(self, assets: list[Asset]) -> list[Quote]:
        """批量获取行情数据，使用批量API优化性能"""
        import asyncio

        quotes = []
        remaining_assets = []

        for asset in assets:
            cache_key = f"quote:{asset.code}"
            cached = await self._cache.async_get(cache_key)
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
        fund_assets = []
        other_assets = []

        for asset in remaining_assets:
            if asset.type == AssetType.FUND:
                fund_assets.append(asset)
            elif asset.market in market_groups:
                market_groups[asset.market].append(asset)
            else:
                other_assets.append(asset)

        # 并行获取各市场数据
        tasks = []

        if market_groups[Market.GLOBAL]:
            secids = [
                f"100.{asset.api_code.split('.')[1] if '.' in asset.api_code else asset.api_code}"
                for asset in market_groups[Market.GLOBAL]
            ]
            tasks.append(self._fetch_global_batch(market_groups[Market.GLOBAL], secids))

        stock_assets = market_groups[Market.CN] + market_groups[Market.HK] + market_groups[Market.US]
        if stock_assets and self._sources:
            tasks.append(self._fetch_from_sources(stock_assets))

        if fund_assets and self._fund_source:
            tasks.append(self._fetch_fund_from_source(fund_assets))

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

    async def _fetch_from_sources(self, assets: list[Asset]) -> list[Quote]:
        quotes = []
        for source in self._sources:
            try:
                fetched = await source.fetch_all(assets)
                if fetched:
                    quotes.extend(fetched)
                    for quote in fetched:
                        asset = next((a for a in assets if a.code == quote.code), None)
                        if asset:
                            ttl = self._cache_strategy.get_ttl(asset.type, asset.market)
                            cache_key = f"quote:{quote.code}"
                            await self._cache.async_set(cache_key, self._quote_to_dict(quote), ttl)
                    break
            except Exception as e:
                logger.warning(f"Source {source.name} failed: {e}")
                continue
        return quotes

    async def _fetch_fund_from_source(self, assets: list[Asset]) -> list[Quote]:
        if not self._fund_source:
            return []
        try:
            fetched = await self._fund_source.fetch_all(assets)
            for quote in fetched:
                asset = next((a for a in assets if a.code == quote.code), None)
                if asset:
                    ttl = self._cache_strategy.get_ttl(asset.type, asset.market)
                    cache_key = f"quote:{quote.code}"
                    await self._cache.async_set(cache_key, self._quote_to_dict(quote), ttl)
            return fetched
        except Exception as e:
            logger.warning(f"Fund source failed: {e}")
            return []

    async def _fetch_others_batch(self, assets: list[Asset]) -> list[Quote]:
        """获取其他类型资产 (单条并发)"""
        import asyncio

        tasks = [self.fetch_single(asset) for asset in assets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, Quote)]

    async def _fetch_global_batch(self, assets: list[Asset], secids: list[str]) -> list[Quote]:
        if not secids:
            return []

        # 使用配置化的URL
        url = self._config.datasource.eastmoney.batch_quote_url
        params = {
            "fltt": 2,
            "invt": 2,
            "secids": ",".join(secids),
            "fields": "f1,f2,f3,f4,f12,f14,f15,f16,f17,f18,f43,f47,f48",
        }

        data = await self._http_client.fetch(url, params=params)

        if not data or not isinstance(data, dict) or data.get("rc") != 0 or not data.get("data"):
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

            # 使用基于资产类型的缓存策略
            ttl = self._cache_strategy.get_ttl(asset.type, asset.market)
            cache_key = f"quote:{asset.code}"
            await self._cache.async_set(cache_key, self._quote_to_dict(quotes[-1]), ttl)

        return quotes
