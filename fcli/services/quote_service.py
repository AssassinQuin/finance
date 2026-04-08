"""Quote Service - 行情查询服务

重构说明:
- 使用依赖注入模式，通过构造函数传入依赖
- 移除全局实例导入，提高可测试性
- 通过 sources 注入数据源，实现策略模式
"""

import asyncio
from datetime import datetime

from ..core.cache_strategy import CacheStrategyBase
from ..core.code_mapper import code_mapper
from ..core.config import Settings
from ..core.interfaces.cache import CacheABC
from ..core.interfaces.source import QuoteSourceABC
from ..core.models import Asset, AssetType, Market, Quote
from ..core.stores.quote import quote_store
from ..infra.http_client import HttpClient
from ..utils.logger import LogContext
from ..utils.logger import quote_logger as logger
from ..utils.time_util import is_trading_hours, utcnow


class QuoteService:
    """行情查询服务

    通过依赖注入接收 cache, config, http_client 等基础设施，
    以及数据源列表 sources，实现解耦和策略模式。

    Args:
        cache: 缓存实例 (CacheABC)
        config: 配置实例 (Settings)
        http_client: HTTP 客户端实例 (HttpClient)
        cache_strategy: 缓存策略实例 (CacheStrategyBase)
        sources: 数据源列表 (List[QuoteSourceABC])
    """

    def __init__(
        self,
        cache: CacheABC,
        config: Settings,
        http_client: HttpClient,
        cache_strategy: CacheStrategyBase,
        sources: list[QuoteSourceABC] | None = None,
        fund_source: QuoteSourceABC | None = None,
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

        if asset.type == AssetType.FUND and self._fund_source:
            try:
                quote = await self._fund_source.fetch_single(asset)
                if quote:
                    return await self._save_quote(quote, "fund_source")
            except Exception as e:
                logger.warning(f"Fund source failed: {e}")
                if not self._config.datasource.fallback_enabled:
                    raise

        source_map = {s.name: s for s in self._sources}

        for source_name in self._config.datasource.quote_priority:
            try:
                source = source_map.get(source_name)
                if not source:
                    continue

                quote = await source.fetch_single(asset)
                if quote:
                    return await self._save_quote(quote, source_name)
            except Exception as e:
                logger.warning(f"Source {source_name} failed: {e}")
                if not self._config.datasource.fallback_enabled:
                    raise
                continue

        return None

    async def _save_quote(self, quote: Quote, source_name: str) -> Quote:
        ttl = self._cache_strategy.get_ttl(quote.type, quote.market)
        cache_key = f"quote:{quote.code}"
        await self._cache.async_set(cache_key, self._quote_to_dict(quote), ttl)
        await quote_store.save(quote)
        logger.info(
            "Quote fetched",
            LogContext(
                operation="fetch_quote",
                code=quote.code,
                market=quote.market.value,
                source=source_name,
                cache_hit=False,
            ),
        )
        return quote

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

    async def fetch_all(self, assets: list[Asset]) -> list[Quote]:
        """批量获取行情数据，使用批量API优化性能"""
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

        market_groups: dict[Market, list[Asset]] = {}
        fund_assets = []

        for asset in remaining_assets:
            if asset.type == AssetType.FUND:
                fund_assets.append(asset)
            else:
                market_groups.setdefault(asset.market, []).append(asset)

        # 并行获取各市场数据
        tasks = []

        global_assets = market_groups.pop(Market.GLOBAL, [])
        if global_assets:
            secids = [code_mapper.to_eastmoney_secid(a.api_code, a.market) for a in global_assets]
            tasks.append(self._fetch_global_batch(global_assets, secids))

        stock_assets = [a for assets in market_groups.values() for a in assets]
        if stock_assets and self._sources:
            tasks.append(self._fetch_from_sources(stock_assets))

        if fund_assets and self._fund_source:
            tasks.append(self._fetch_fund_from_source(fund_assets))

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

    async def _fetch_global_batch(self, assets: list[Asset], secids: list[str]) -> list[Quote]:
        if not secids:
            return []

        em = self._config.datasource.eastmoney
        url = em.batch_quote_url
        params = {
            "fltt": 2,
            "invt": 2,
            "secids": ",".join(secids),
            "fields": em.BATCH_FIELDS,
        }

        data = await self._http_client.fetch(url, params=params)

        if not data or not isinstance(data, dict) or data.get("rc") != 0 or not data.get("data"):
            return []

        quotes = []
        asset_map = {
            asset.api_code.split(".")[1] if "." in asset.api_code else asset.api_code: asset for asset in assets
        }

        for item in data["data"].get("diff", []):
            code = item.get(em.F_BATCH_CODE)
            if not code or code not in asset_map:
                continue

            asset = asset_map[code]
            price = float(item.get(em.F_BATCH_PRICE, 0)) if item.get(em.F_BATCH_PRICE) else 0.0
            change_percent = float(item.get(em.F_BATCH_CHANGE, 0)) if item.get(em.F_BATCH_CHANGE) else 0.0

            quotes.append(
                Quote(
                    code=asset.code,
                    name=item.get(em.F_BATCH_NAME, asset.name),
                    price=price,
                    change_percent=change_percent,
                    update_time=utcnow(),
                    market=asset.market,
                    type=asset.type,
                    high=float(item.get(em.F_BATCH_HIGH, 0)) if item.get(em.F_BATCH_HIGH) else None,
                    low=float(item.get(em.F_BATCH_LOW, 0)) if item.get(em.F_BATCH_LOW) else None,
                    volume=float(item.get(em.F_BATCH_VOLUME, 0))
                    if item.get(em.F_BATCH_VOLUME) and item.get(em.F_BATCH_VOLUME) != "-"
                    else None,
                )
            )

            ttl = self._cache_strategy.get_ttl(asset.type, asset.market)
            cache_key = f"quote:{asset.code}"
            await self._cache.async_set(cache_key, self._quote_to_dict(quotes[-1]), ttl)

        return quotes
