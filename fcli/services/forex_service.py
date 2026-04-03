"""
汇率查询服务
支持 Frankfurter API (欧洲央行汇率) 和 ExchangeRate-API
"""

import asyncio

from ..core.cache import cache
from ..core.config import Settings, config
from ..core.interfaces.cache import CacheABC
from ..core.interfaces.source import ForexSourceABC
from ..core.models import ExchangeRate
from ..core.stores.exchange_rate import exchange_rate_store
from ..infra.http_client import HttpClient, http_client
from ..utils.currency import COMMON_CURRENCIES


class ForexService:
    """汇率查询服务"""

    def __init__(
        self,
        sources: list[ForexSourceABC],
        cache_backend: CacheABC | None = None,
        settings: Settings | None = None,
        client: HttpClient | None = None,
    ):
        self._sources = sources
        self._cache = cache_backend or cache
        self._config = settings or config
        self._http_client = client or http_client

    def _source_by_name(self, name: str) -> ForexSourceABC | None:
        for source in self._sources:
            if source.name == name:
                return source
        return None

    async def get_rate(self, base_currency: str, quote_currency: str) -> ExchangeRate | None:
        """获取两个货币之间的汇率"""
        base_currency = base_currency.upper()
        quote_currency = quote_currency.upper()

        cache_key = f"forex:{base_currency}:{quote_currency}"
        cached = await self._cache.async_get(cache_key)
        if cached:
            return ExchangeRate(**cached)

        for source_name in self._config.datasource.forex_priority:
            source = self._source_by_name(source_name)
            if source is None:
                continue
            try:
                rate = await source.fetch_rate(base_currency, quote_currency)
                if rate:
                    await self._cache.async_set(
                        cache_key,
                        {
                            "base_currency": rate.base_currency,
                            "quote_currency": rate.quote_currency,
                            "rate": rate.rate,
                            "source": rate.source,
                            "update_time": rate.update_time.isoformat() if rate.update_time else None,
                        },
                        self._config.cache.forex_ttl,
                    )
                    await exchange_rate_store.save(rate)
                    return rate

            except Exception:
                if not self._config.datasource.fallback_enabled:
                    raise
                continue

        return None

    async def get_all_rates(self, base_currency: str = "USD") -> dict[str, ExchangeRate]:
        """获取基准货币对所有常用货币的汇率"""
        base_currency = base_currency.upper()
        rates = {}

        cache_key = f"forex:all:{base_currency}"
        cached = await self._cache.async_get(cache_key)
        if cached:
            for code, data in cached.items():
                rates[code] = ExchangeRate(**data)
            return rates

        tasks = []
        for currency in COMMON_CURRENCIES:
            if currency != base_currency:
                tasks.append(self.get_rate(base_currency, currency))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, ExchangeRate):
                rates[result.quote_currency] = result

        cache_data = {
            code: {
                "base_currency": rate.base_currency,
                "quote_currency": rate.quote_currency,
                "rate": rate.rate,
                "source": rate.source,
                "update_time": rate.update_time.isoformat() if rate.update_time else None,
            }
            for code, rate in rates.items()
        }
        await self._cache.async_set(cache_key, cache_data, self._config.cache.forex_ttl)

        return rates
