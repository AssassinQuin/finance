"""
汇率查询服务
支持 Frankfurter API (欧洲央行汇率) 和 ExchangeRate-API
"""

import asyncio
from datetime import datetime

from ..core.cache import cache
from ..core.config import config
from ..core.models import ExchangeRate
from ..core.stores.exchange_rate_fact import ExchangeRateFactStore
from ..infra.http_client import http_client


class ForexService:
    """汇率查询服务"""

    COMMON_CURRENCIES = {
        "USD": "美元",
        "CNY": "人民币",
        "EUR": "欧元",
        "GBP": "英镑",
        "JPY": "日元",
        "KRW": "韩元",
        "HKD": "港币",
        "TWD": "新台币",
        "SGD": "新加坡元",
        "AUD": "澳元",
        "CAD": "加元",
        "CHF": "瑞士法郎",
        "THB": "泰铢",
        "MYR": "马来西亚林吉特",
        "INR": "印度卢比",
        "RUB": "俄罗斯卢布",
    }

    async def get_rate(self, base_currency: str, quote_currency: str) -> ExchangeRate | None:
        """获取两个货币之间的汇率"""
        base_currency = base_currency.upper()
        quote_currency = quote_currency.upper()

        cache_key = f"forex:{base_currency}:{quote_currency}"
        cached = await cache.async_get(cache_key)
        if cached:
            return ExchangeRate(**cached)

        for source in config.datasource.forex_priority:
            try:
                if source == "frankfurter":
                    rate = await self._fetch_frankfurter(base_currency, quote_currency)
                elif source == "exchangerate":
                    rate = await self._fetch_exchangerate(base_currency, quote_currency)
                else:
                    continue

                if rate:
                    await cache.async_set(
                        cache_key,
                        {
                            "base_currency": rate.base_currency,
                            "quote_currency": rate.quote_currency,
                            "rate": rate.rate,
                            "source": rate.source,
                            "update_time": rate.update_time.isoformat() if rate.update_time else None,
                        },
                        config.cache.forex_ttl,
                    )
                    await ExchangeRateFactStore.save(rate)
                    return rate

            except Exception:
                if not config.datasource.fallback_enabled:
                    raise
                continue

        return None

    async def _fetch_frankfurter(self, base_currency: str, quote_currency: str) -> ExchangeRate | None:
        """从 Frankfurter API 获取汇率 (欧洲央行数据)"""
        url = f"{config.datasource.forex.frankfurter_base_url}/latest"
        params = {
            "from": base_currency,
            "to": quote_currency,
        }

        data = await http_client.fetch(url, params=params)

        if not data or "rates" not in data:
            return None

        rate = data["rates"].get(quote_currency)
        if rate is None:
            return None

        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        update_time = datetime.strptime(date_str, "%Y-%m-%d")

        return ExchangeRate(
            base_currency=base_currency,
            quote_currency=quote_currency,
            rate=float(rate),
            source="Frankfurter (ECB)",
            update_time=update_time,
        )

    async def _fetch_exchangerate(self, base_currency: str, quote_currency: str) -> ExchangeRate | None:
        """从 ExchangeRate-API 获取汇率"""
        url = f"{config.datasource.forex.exchangerate_base_url}/v6/latest/{base_currency}"

        data = await http_client.fetch(url)

        if not data or "rates" not in data:
            return None

        rate = data["rates"].get(quote_currency)
        if rate is None:
            return None

        return ExchangeRate(
            base_currency=base_currency,
            quote_currency=quote_currency,
            rate=float(rate),
            source="ExchangeRate-API",
            update_time=datetime.now(),
        )

    async def get_all_rates(self, base_currency: str = "USD") -> dict[str, ExchangeRate]:
        """获取基准货币对所有常用货币的汇率"""
        base_currency = base_currency.upper()
        rates = {}

        cache_key = f"forex:all:{base_currency}"
        cached = cache.get(cache_key)
        if cached:
            for code, data in cached.items():
                rates[code] = ExchangeRate(**data)
            return rates

        tasks = []
        for currency in self.COMMON_CURRENCIES:
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
        cache.set(cache_key, cache_data, config.cache.forex_ttl)

        return rates

    def get_currency_name(self, code: str) -> str:
        """获取货币中文名称"""
        return self.COMMON_CURRENCIES.get(code.upper(), code)

    def format_currency_display(self, code: str) -> str:
        """格式化货币显示：代码（中文名）或仅代码"""
        name = self.COMMON_CURRENCIES.get(code.upper())
        return f"{code}（{name}）" if name else code


forex_service = ForexService()
