"""
汇率查询服务
支持 Frankfurter API (欧洲央行汇率) 和 ExchangeRate-API
"""

import asyncio
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

from ..core.cache import cache
from ..core.config import config
from ..infra.http_client import http_client


@dataclass
class ExchangeRate:
    from_currency: str
    to_currency: str
    rate: float
    date: str
    source: str


class ForexService:
    """汇率查询服务"""

    # 常用货币代码
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

    async def get_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """获取两个货币之间的汇率"""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # 检查缓存
        cache_key = f"forex:{from_currency}:{to_currency}"
        cached = cache.get(cache_key)
        if cached:
            return ExchangeRate(**cached)

        # 按优先级尝试不同的数据源
        for source in config.source.forex_priority:
            try:
                if source == "frankfurter":
                    rate = await self._fetch_frankfurter(from_currency, to_currency)
                elif source == "exchangerate":
                    rate = await self._fetch_exchangerate(from_currency, to_currency)
                else:
                    continue

                if rate:
                    # 存入缓存
                    cache.set(
                        cache_key,
                        {
                            "from_currency": rate.from_currency,
                            "to_currency": rate.to_currency,
                            "rate": rate.rate,
                            "date": rate.date,
                            "source": rate.source,
                        },
                        config.cache.forex_ttl,
                    )
                    return rate

            except Exception as e:
                if not config.source.fallback_enabled:
                    raise
                continue

        return None

    async def _fetch_frankfurter(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """从 Frankfurter API 获取汇率 (欧洲央行数据)"""
        url = f"https://api.frankfurter.app/latest"
        params = {
            "from": from_currency,
            "to": to_currency,
        }

        data = await http_client.fetch(url, params=params)

        if not data or "rates" not in data:
            return None

        rate = data["rates"].get(to_currency)
        if rate is None:
            return None

        return ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=float(rate),
            date=data.get("date", datetime.now().strftime("%Y-%m-%d")),
            source="Frankfurter (ECB)",
        )

    async def _fetch_exchangerate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """从 ExchangeRate-API 获取汇率"""
        # 使用免费的公开 API
        url = f"https://open.er-api.com/v6/latest/{from_currency}"

        data = await http_client.fetch(url)

        if not data or "rates" not in data:
            return None

        rate = data["rates"].get(to_currency)
        if rate is None:
            return None

        return ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=float(rate),
            date=datetime.now().strftime("%Y-%m-%d"),
            source="ExchangeRate-API",
        )

    async def get_all_rates(self, base_currency: str = "USD") -> Dict[str, ExchangeRate]:
        """获取基准货币对所有常用货币的汇率"""
        base_currency = base_currency.upper()
        rates = {}

        # 检查缓存
        cache_key = f"forex:all:{base_currency}"
        cached = cache.get(cache_key)
        if cached:
            for code, data in cached.items():
                rates[code] = ExchangeRate(**data)
            return rates

        # 获取所有汇率
        tasks = []
        for currency in self.COMMON_CURRENCIES:
            if currency != base_currency:
                tasks.append(self.get_rate(base_currency, currency))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, ExchangeRate):
                rates[result.to_currency] = result

        # 存入缓存
        cache_data = {
            code: {
                "from_currency": rate.from_currency,
                "to_currency": rate.to_currency,
                "rate": rate.rate,
                "date": rate.date,
                "source": rate.source,
            }
            for code, rate in rates.items()
        }
        cache.set(cache_key, cache_data, config.cache.forex_ttl)

        return rates

    def get_currency_name(self, code: str) -> str:
        """获取货币中文名称"""
        return self.COMMON_CURRENCIES.get(code.upper(), code)


forex_service = ForexService()
