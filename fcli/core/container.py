"""Lightweight Dependency Injection Container.

A minimal DI container that manages service lifecycle and dependencies.
Supports lazy initialization, async setup, and testing overrides.

Design Principles:
- Zero external dependencies
- Lazy initialization (services created on first access)
- Type-safe with full type hints
- Thread-safe singleton management
- Easy testing via override mechanism

Usage:
    # Production usage
    from fcli.core.container import Container

    container = Container()
    quote_service = container.quote_service

    # Testing with overrides
    container.override("quote_service", mock_quote_service)
    # Now container.quote_service returns the mock

    # Async initialization (if needed)
    await container.init_async()
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
)

if TYPE_CHECKING:
    from ..infra.http_client import HttpClient
    from ..services.forex_service import ForexService
    from ..services.gold_service import GoldService
    from ..services.gpr_service import GPRService
    from ..services.quote_service import QuoteService
    from .cache import Cache
    from .config import Settings
    from .database import Database
    from .storage import Storage

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLifetime(Enum):
    """Service lifetime modes."""

    SINGLETON = auto()  # Created once, reused
    TRANSIENT = auto()  # Created every time
    SCOPED = auto()  # Created once per scope (future use)


@dataclass
class ServiceDescriptor(Generic[T]):
    """Describes how a service should be created and managed."""

    factory: Callable[[], T]
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    instance: T | None = None
    initialized: bool = False


class Container:
    """Lightweight dependency injection container.

    Features:
    - Lazy initialization: Services created on first access
    - Singleton & transient lifetimes
    - Override support for testing
    - Async initialization support
    - Thread-safe instance management

    Example:
        >>> container = Container()
        >>> service = container.quote_service
        >>> await container.shutdown()
    """

    def __init__(self, config: Settings | None = None):
        """Initialize container with optional config override.

        Args:
            config: Settings instance (uses global config if not provided)
        """
        self._config = config
        self._services: dict[str, ServiceDescriptor] = {}
        self._overrides: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

        # Register all services
        self._register_services()

    @property
    def config(self) -> Settings:
        """Get configuration (lazy loaded)."""
        if self._config is None:
            from .config import config

            self._config = config
        return self._config

    def _register_services(self) -> None:
        """Register all application services.

        Services are registered with factories that will be called lazily.
        This avoids circular imports and keeps startup fast.
        """
        # Infrastructure services
        self._register("http_client", self._create_http_client)
        self._register("cache", self._create_cache)
        self._register("database", self._create_database)
        self._register("storage", self._create_storage)

        # Application services
        self._register("quote_service", self._create_quote_service)
        self._register("gold_service", self._create_gold_service)
        self._register("gpr_service", self._create_gpr_service)
        self._register("forex_service", self._create_forex_service)

    def _register(
        self, name: str, factory: Callable[[], T], lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    ) -> None:
        """Register a service with its factory.

        Args:
            name: Service identifier
            factory: Function that creates the service
            lifetime: Service lifetime mode
        """
        self._services[name] = ServiceDescriptor(factory=factory, lifetime=lifetime)

    def _get(self, name: str) -> Any:
        """Get or create a service instance.

        Args:
            name: Service identifier

        Returns:
            Service instance
        """
        # Check for test override first
        if name in self._overrides:
            return self._overrides[name]

        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")

        descriptor = self._services[name]

        # Return existing singleton instance
        if descriptor.lifetime == ServiceLifetime.SINGLETON and descriptor.initialized:
            return descriptor.instance

        # Create new instance
        instance = descriptor.factory()

        # Cache singleton
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            descriptor.instance = instance
            descriptor.initialized = True

        return instance

    # =========================================================================
    # Service Properties (Public API)
    # =========================================================================

    @property
    def http_client(self) -> HttpClient:
        """HTTP client for network requests."""
        return self._get("http_client")

    @property
    def cache(self) -> Cache:
        """Cache service for data caching."""
        return self._get("cache")

    @property
    def database(self) -> Database:
        """Database connection manager."""
        return self._get("database")

    @property
    def storage(self) -> Storage:
        """Storage service for watchlist assets."""
        return self._get("storage")

    @property
    def quote_service(self) -> QuoteService:
        """Quote data service."""
        return self._get("quote_service")

    @property
    def gold_service(self) -> GoldService:
        """Gold reserve data service."""
        return self._get("gold_service")

    @property
    def gpr_service(self) -> GPRService:
        """Geopolitical risk index service."""
        return self._get("gpr_service")

    @property
    def forex_service(self) -> ForexService:
        """Foreign exchange service."""
        return self._get("forex_service")

    # =========================================================================
    # Service Factories
    # =========================================================================

    def _create_http_client(self) -> HttpClient:
        """Create HTTP client instance."""
        from ..infra.http_client import HttpClient

        return HttpClient(max_retries=3, retry_delay=1.0)

    def _create_cache(self) -> Cache:
        """Create cache instance."""
        from .cache import Cache

        return Cache()

    def _create_database(self) -> Database:
        """Create database instance (returns class, not instance)."""
        from .database import Database

        return Database

    def _create_storage(self) -> Storage:
        """Create storage instance."""
        from .storage import Storage

        return Storage()

    def _create_quote_service(self) -> QuoteService:
        """Create quote service instance."""
        from ..services.quote_service import QuoteService

        return QuoteService()

    def _create_gold_service(self) -> GoldService:
        """Create gold service instance."""
        from ..services.gold_service import GoldService

        return GoldService()

    def _create_gpr_service(self) -> GPRService:
        """Create GPR service instance."""
        from ..services.gpr_service import GPRService

        return GPRService()

    def _create_forex_service(self) -> ForexService:
        """Create forex service instance."""
        from ..services.forex_service import ForexService

        return ForexService()

    # =========================================================================
    # Testing Support
    # =========================================================================

    def override(self, name: str, instance: Any) -> None:
        """Override a service for testing.

        Args:
            name: Service identifier
            instance: Mock or replacement instance

        Example:
            >>> container.override("quote_service", MockQuoteService())
            >>> assert container.quote_service.__class__.__name__ == "MockQuoteService"
        """
        self._overrides[name] = instance
        logger.debug(f"Service '{name}' overridden")

    def reset_override(self, name: str) -> None:
        """Remove a service override.

        Args:
            name: Service identifier
        """
        if name in self._overrides:
            del self._overrides[name]
            logger.debug(f"Override for '{name}' removed")

    def reset_all_overrides(self) -> None:
        """Remove all service overrides."""
        self._overrides.clear()
        logger.debug("All overrides removed")

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    async def init_async(self) -> bool:
        """Initialize async resources (database, etc).

        Returns:
            True if initialization succeeded
        """
        if self._initialized:
            return True

        async with self._lock:
            if self._initialized:
                return True

            # Initialize database if configured
            try:
                from .database import Database

                await Database.init(self.config)
                self._initialized = True
                logger.info("Container async initialization complete")
                return True
            except Exception as e:
                logger.error(f"Container async initialization failed: {e}")
                return False

    async def shutdown(self) -> None:
        """Cleanup all resources.

        Closes HTTP clients, database connections, etc.
        """
        # Close HTTP client
        try:
            http_client = self._services.get("http_client")
            if http_client and http_client.instance:
                await http_client.instance.close()
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")

        # Close gold service
        try:
            gold_service = self._services.get("gold_service")
            if gold_service and gold_service.instance:
                await gold_service.instance.close()
        except Exception as e:
            logger.warning(f"Error closing gold service: {e}")

        # Close database
        try:
            from .database import Database

            await Database.close()
        except Exception as e:
            logger.warning(f"Error closing database: {e}")

        self._initialized = False
        logger.info("Container shutdown complete")

    def reset(self) -> None:
        """Reset all singleton instances.

        Useful for testing to get fresh instances.
        """
        for descriptor in self._services.values():
            descriptor.instance = None
            descriptor.initialized = False

        self._initialized = False
        logger.debug("Container reset")

    # =========================================================================
    # Introspection
    # =========================================================================

    def get_registered_services(self) -> dict[str, str]:
        """Get list of registered services and their lifetimes.

        Returns:
            Dict mapping service name to lifetime name
        """
        return {name: desc.lifetime.name for name, desc in self._services.items()}

    def is_overridden(self, name: str) -> bool:
        """Check if a service is overridden.

        Args:
            name: Service identifier

        Returns:
            True if service has an override
        """
        return name in self._overrides


# =============================================================================
# Global Container Instance
# =============================================================================

# Global container for convenience
# In production, use dependency injection instead of this global
_container: Container | None = None


def get_container() -> Container:
    """Get the global container instance.

    Creates container on first call (lazy initialization).

    Returns:
        Global Container instance
    """
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """Reset the global container.

    Useful for testing to ensure clean state.
    """
    global _container
    _container = None


__all__ = [
    "Container",
    "ServiceLifetime",
    "ServiceDescriptor",
    "get_container",
    "reset_container",
]
