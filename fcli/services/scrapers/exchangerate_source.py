"""ExchangeRate-API 汇率数据源"""

from ...core.config import Settings
from ...core.interfaces.source import ForexSourceABC
from ...core.models import ExchangeRate
from ...infra.http_client import HttpClient
from ...utils.time_util import utcnow


class ExchangeRateSource(ForexSourceABC):
    """ExchangeRate-API 汇率数据源"""

    def __init__(self, http_client: HttpClient, config: Settings):
        self._http_client = http_client
        self._config = config

    @property
    def name(self) -> str:
        return "exchangerate"

    async def is_available(self) -> bool:
        return True

    async def fetch_rate(self, base_currency: str, quote_currency: str) -> ExchangeRate | None:
        url = f"{self._config.datasource.forex.exchangerate_base_url}/v6/latest/{base_currency}"

        data = await self._http_client.fetch(url)

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
            update_time=utcnow(),
        )
