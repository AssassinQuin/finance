"""Frankfurter API (欧洲央行) 汇率数据源"""

from datetime import datetime

from ...core.config import Settings
from ...core.interfaces.source import ForexSourceABC
from ...core.models import ExchangeRate
from ...infra.http_client import HttpClient
from ...utils.time_util import DATE_FORMAT, utcnow


class FrankfurterSource(ForexSourceABC):
    """Frankfurter API 汇率数据源 (欧洲央行数据)"""

    def __init__(self, http_client: HttpClient, config: Settings):
        self._http_client = http_client
        self._config = config

    @property
    def name(self) -> str:
        return "frankfurter"

    async def is_available(self) -> bool:
        return True

    async def fetch_rate(self, base_currency: str, quote_currency: str) -> ExchangeRate | None:
        url = f"{self._config.datasource.forex.frankfurter_base_url}/latest"
        params = {
            "from": base_currency,
            "to": quote_currency,
        }

        data = await self._http_client.fetch(url, params=params)

        if not data or "rates" not in data:
            return None

        rate = data["rates"].get(quote_currency)
        if rate is None:
            return None

        date_str = data.get("date", utcnow().strftime(DATE_FORMAT))
        update_time = datetime.strptime(date_str, DATE_FORMAT)

        return ExchangeRate(
            base_currency=base_currency,
            quote_currency=quote_currency,
            rate=float(rate),
            source="Frankfurter (ECB)",
            update_time=update_time,
        )
