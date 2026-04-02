"""Dependency injection container.

Centralized management of all service dependencies for decoupling and testability.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from ..infra.http_client import HttpClient, http_client
from .cache import HybridCache
from .cache_strategy import AssetTypeCacheStrategy, CacheStrategyBase
from .config import Settings, config
from .interfaces.cache import CacheABC
from .interfaces.storage import StorageABC
from .storage import HybridStorage

if TYPE_CHECKING:
    from ..services.forex_service import ForexService
    from ..services.fund_service import FundService
    from ..services.gold_reserve_service import GoldReserveService
    from ..services.gold_supply_demand_service import GoldSupplyDemandService
    from ..services.gpr_service import GPRService
    from ..services.quote_service import QuoteService
    from ..services.watchlist_service import WatchlistService


class Container:
    """Dependency injection container.

    Manages all service instances with:
    - Lazy initialization
    - Singleton pattern
    - Replaceable dependencies (for testing)
    """

    def __init__(self, settings: Settings | None = None):
        self._config = settings or config

        self._cache: CacheABC | None = None
        self._storage: StorageABC | None = None
        self._http_client: HttpClient | None = None
        self._cache_strategy: CacheStrategyBase | None = None
        self._quote_service: QuoteService | None = None
        self._gold_reserve_service: GoldReserveService | None = None
        self._gold_supply_demand_service: GoldSupplyDemandService | None = None
        self._forex_service: ForexService | None = None
        self._gpr_service: GPRService | None = None
        self._fund_service: FundService | None = None
        self._watchlist_service: WatchlistService | None = None

    @property
    def config(self) -> Settings:
        return self._config

    @property
    def cache(self) -> CacheABC:
        if self._cache is None:
            self._cache = HybridCache()
        return self._cache

    @property
    def storage(self) -> StorageABC:
        if self._storage is None:
            self._storage = HybridStorage()
        return self._storage

    @property
    def http_client(self) -> HttpClient:
        if self._http_client is None:
            self._http_client = http_client
        return self._http_client

    @property
    def cache_strategy(self) -> CacheStrategyBase:
        if self._cache_strategy is None:
            self._cache_strategy = AssetTypeCacheStrategy.from_config(self._config)
        return self._cache_strategy

    @property
    def quote_service(self) -> QuoteService:
        if self._quote_service is None:
            from ..services.quote_service import QuoteService
            from ..services.scrapers.eastmoney_quote_source import EastmoneyQuoteSource
            from ..services.scrapers.fund_quote_source import FundQuoteSource
            from ..services.scrapers.sina_quote_source import SinaQuoteSource

            sina_source = SinaQuoteSource(
                http_client=self.http_client,
                config=self._config,
            )
            eastmoney_source = EastmoneyQuoteSource(
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
                sources=[sina_source, eastmoney_source],
                fund_source=fund_source,
            )
        return self._quote_service

    @property
    def gold_reserve_service(self) -> GoldReserveService:
        if self._gold_reserve_service is None:
            from ..services.gold_reserve_service import GoldReserveService
            from ..services.scrapers.imf_scraper import IMFScraper

            self._gold_reserve_service = GoldReserveService(
                imf_scraper=IMFScraper(
                    http_client=self.http_client,
                    settings=self._config,
                ),
            )
        return self._gold_reserve_service

    @property
    def gold_supply_demand_service(self) -> GoldSupplyDemandService:
        if self._gold_supply_demand_service is None:
            from ..services.gold_supply_demand_service import GoldSupplyDemandService
            from ..services.scrapers.wgc_scraper import WGCScraper

            self._gold_supply_demand_service = GoldSupplyDemandService(
                wgc_scraper=WGCScraper(
                    http_client=self.http_client,
                ),
            )
        return self._gold_supply_demand_service

    @property
    def forex_service(self) -> ForexService:
        if self._forex_service is None:
            from ..services.forex_service import ForexService
            from ..services.scrapers.exchangerate_source import ExchangeRateSource
            from ..services.scrapers.frankfurter_source import FrankfurterSource

            sources = [
                FrankfurterSource(http_client=self.http_client, config=self._config),
                ExchangeRateSource(http_client=self.http_client, config=self._config),
            ]
            self._forex_service = ForexService(
                sources=sources,
                cache_backend=self.cache,
                settings=self._config,
                client=self.http_client,
            )
        return self._forex_service

    @property
    def gpr_service(self) -> GPRService:
        if self._gpr_service is None:
            from ..services.gpr_service import GPRService
            from ..services.scrapers.gpr_scraper import GPRScraper

            self._gpr_service = GPRService(
                settings=self._config,
                gpr_scraper=GPRScraper(),
            )
        return self._gpr_service

    @property
    def fund_service(self) -> FundService:
        if self._fund_service is None:
            from ..services.fund_service import FundService
            from ..services.scrapers.fund_scraper import FundScraper

            self._fund_service = FundService(
                fund_scraper=FundScraper(),
            )
        return self._fund_service

    @property
    def watchlist_service(self) -> WatchlistService:
        if self._watchlist_service is None:
            from ..services.watchlist_service import WatchlistService

            self._watchlist_service = WatchlistService(
                storage=self.storage,
            )
        return self._watchlist_service

    @asynccontextmanager
    async def session(self):
        from .database import Database

        async with Database.session(self._config):
            yield

    async def cleanup(self):
        if self._http_client is not None:
            await self._http_client.close()
            self._http_client = None


container = Container()
