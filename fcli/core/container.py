"""Dependency injection container.

Centralized management of all service dependencies for decoupling and testability.
"""


from ..infra.http_client import HttpClient, http_client
from .cache import HybridCache
from .cache_strategy import AssetTypeCacheStrategy, ICacheStrategy
from .config import Settings, config
from .interfaces.cache import ICache
from .interfaces.storage import IStorage
from .storage import HybridStorage


class Container:
    """Dependency injection container.

    Manages all service instances with:
    - Lazy initialization
    - Singleton pattern
    - Replaceable dependencies (for testing)
    """

    def __init__(self, settings: Settings | None = None):
        self._config = settings or config

        self._cache: ICache | None = None
        self._storage: IStorage | None = None
        self._http_client: HttpClient | None = None
        self._cache_strategy: ICacheStrategy | None = None
        self._quote_service = None
        self._gold_service = None
        self._forex_service = None
        self._gpr_service = None

    @property
    def config(self) -> Settings:
        return self._config

    @property
    def cache(self) -> ICache:
        if self._cache is None:
            self._cache = HybridCache()
        return self._cache

    @property
    def storage(self) -> IStorage:
        if self._storage is None:
            self._storage = HybridStorage()
        return self._storage

    @property
    def http_client(self) -> HttpClient:
        if self._http_client is None:
            self._http_client = http_client
        return self._http_client

    @property
    def cache_strategy(self) -> ICacheStrategy:
        if self._cache_strategy is None:
            self._cache_strategy = AssetTypeCacheStrategy.from_config(self._config)
        return self._cache_strategy

    @property
    def quote_service(self):
        if self._quote_service is None:
            from ..services.quote_service import QuoteService
            from ..services.scrapers.fund_quote_source import FundQuoteSource
            from ..services.scrapers.sina_quote_source import SinaQuoteSource

            sina_source = SinaQuoteSource(
                http_client=self.http_client,
                config=self._config,
            )
            fund_source = FundQuoteSource(
                http_client=self.http_client,
                config=self._config,
            )
            self._quote_service = QuoteService(
                cache=self.cache,
                config=self._config,
                http_client=self.http_client,
                cache_strategy=self.cache_strategy,
                sources=[sina_source],
                fund_source=fund_source,
            )
        return self._quote_service

    @property
    def gold_service(self):
        if self._gold_service is None:
            from ..services.gold_service import GoldService

            self._gold_service = GoldService()
        return self._gold_service

    @property
    def forex_service(self):
        if self._forex_service is None:
            from ..services.forex_service import ForexService

            self._forex_service = ForexService()
        return self._forex_service

    @property
    def gpr_service(self):
        if self._gpr_service is None:
            from ..services.gpr_service import GPRService

            self._gpr_service = GPRService()
        return self._gpr_service

    async def cleanup(self):
        if self._http_client is not None:
            await self._http_client.close()
            self._http_client = None


container = Container()
