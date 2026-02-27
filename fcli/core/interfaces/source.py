"""Data Source Abstract Interfaces.

Defines contracts for data source services (Quote, Gold, Forex, GPR).
All specialized sources inherit from the base DataSource class.

This module provides both Protocol and ABC based interfaces:
- Protocol: Structural subtyping (duck typing with type checking)
- ABC: Nominal subtyping (explicit inheritance)

Use Protocol for flexibility, ABC when you need to enforce inheritance.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..models import Asset, ExchangeRate, Market, Quote


# =============================================================================
# Base Data Source Interface
# =============================================================================


@runtime_checkable
class IDataSource(Protocol):
    """Protocol for all data sources with common contract."""

    @property
    def name(self) -> str:
        """Unique identifier for this data source (e.g., "sina", "eastmoney")."""
        ...

    @property
    def priority(self) -> int:
        """Priority level for source selection (higher = preferred)."""
        ...

    @property
    def supported_markets(self) -> "list[Market]":
        """List of markets this source can handle."""
        ...

    async def is_available(self) -> bool:
        """Check if the data source is currently available and healthy."""
        ...


class DataSourceABC(ABC):
    """
    Abstract base class for all data sources.

    Defines the minimal interface that every data source must implement.
    Used as the foundation for source selection strategy and health monitoring.

    Attributes:
        name: Unique identifier for this data source (e.g., "sina", "eastmoney").
        priority: Priority level for source selection (higher = preferred).
        supported_markets: List of markets this source can handle.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique identifier for this data source."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Return the priority level for source selection.

        Higher values indicate higher priority (preferred source).
        Typical values: 100 (primary), 50 (fallback), 10 (last resort).
        """
        pass

    @property
    @abstractmethod
    def supported_markets(self) -> "list[Market]":
        """Return the list of markets this source supports."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the data source is currently available and healthy.

        Should perform a lightweight health check (e.g., ping endpoint).

        Returns:
            True if the source is available, False otherwise.
        """
        pass


# =============================================================================
# Quote Source Interface
# =============================================================================


@runtime_checkable
class IQuoteSource(Protocol):
    """Protocol for quote data sources."""

    @property
    def name(self) -> str:
        """Unique identifier for this data source."""
        ...

    @property
    def priority(self) -> int:
        """Priority level for source selection."""
        ...

    @property
    def supported_markets(self) -> "list[Market]":
        """List of markets this source can handle."""
        ...

    async def is_available(self) -> bool:
        """Check if the data source is currently available."""
        ...

    async def fetch_single(self, asset: "Asset") -> "Quote | None":
        """Fetch quote for a single asset.

        Args:
            asset: Asset to fetch quote for

        Returns:
            Quote if available, None otherwise
        """
        ...

    async def fetch_all(self, assets: "list[Asset]") -> "list[Quote]":
        """Fetch quotes for multiple assets.

        Args:
            assets: List of assets to fetch quotes for

        Returns:
            List of successfully fetched quotes
        """
        ...


class QuoteSourceABC(DataSourceABC):
    """
    Abstract base class for stock/fund quote sources.

    Specializes DataSource for fetching real-time quotes for stocks,
    funds, and indices. Examples: Sina, Eastmoney, Yahoo Finance.
    """

    @abstractmethod
    async def fetch_single(self, asset: "Asset") -> "Quote | None":
        """
        Fetch quote for a single asset.

        Args:
            asset: The asset to fetch quote data for.

        Returns:
            Quote object if successful, None if fetch failed or
            data not available for this asset.
        """
        pass

    @abstractmethod
    async def fetch_all(self, assets: "list[Asset]") -> "list[Quote]":
        """
        Fetch quotes for multiple assets.

        Args:
            assets: List of assets to fetch quotes for.

        Returns:
            List of successfully fetched Quote objects.
        """
        pass


# =============================================================================
# Gold Source Interface
# =============================================================================


@runtime_checkable
class IGoldSource(Protocol):
    """Protocol for gold reserve data sources."""

    @property
    def name(self) -> str:
        """Unique identifier for this data source."""
        ...

    @property
    def priority(self) -> int:
        """Priority level for source selection."""
        ...

    @property
    def supported_markets(self) -> "list[Market]":
        """List of markets this source can handle."""
        ...

    async def is_available(self) -> bool:
        """Check if the data source is currently available."""
        ...

    async def get_latest(self, country_codes: list[str] | None = None) -> list[dict[str, Any]]:
        """Get latest gold reserves.

        Args:
            country_codes: Optional filter by country codes

        Returns:
            List of reserve data dicts
        """
        ...

    async def get_history(self, country_code: str, months: int = 120) -> list[dict[str, Any]]:
        """Get historical gold reserves for a country.

        Args:
            country_code: ISO 3-letter country code
            months: Number of months of history

        Returns:
            List of historical data dicts
        """
        ...

    async def close(self) -> None:
        """Close resources."""
        ...


class GoldSourceABC(DataSourceABC):
    """
    Abstract base class for gold reserve data sources.

    Specializes DataSource for fetching central bank gold reserve data.
    Examples: World Gold Council, IMF, Federal Reserve.
    """

    @property
    def supported_markets(self) -> "list[Market]":
        """Gold sources only support the GLOBAL market."""
        from ..models import Market

        return [Market.GLOBAL]

    @abstractmethod
    async def get_latest(self, country_codes: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Get latest gold reserves.

        Args:
            country_codes: Optional filter by country codes.

        Returns:
            List of reserve data dicts.
        """
        pass

    @abstractmethod
    async def get_history(self, country_code: str, months: int = 120) -> list[dict[str, Any]]:
        """
        Get historical gold reserves for a country.

        Args:
            country_code: ISO 3-letter country code.
            months: Number of months of history.

        Returns:
            List of historical data dicts.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close resources."""
        pass


# =============================================================================
# Forex Source Interface
# =============================================================================


@runtime_checkable
class IForexSource(Protocol):
    """Protocol for foreign exchange data sources."""

    @property
    def name(self) -> str:
        """Unique identifier for this data source."""
        ...

    @property
    def priority(self) -> int:
        """Priority level for source selection."""
        ...

    @property
    def supported_markets(self) -> "list[Market]":
        """List of markets this source can handle."""
        ...

    async def is_available(self) -> bool:
        """Check if the data source is currently available."""
        ...

    async def get_rate(self, from_currency: str, to_currency: str) -> Any | None:
        """Get exchange rate between two currencies.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            ExchangeRate-like object or None
        """
        ...

    async def get_all_rates(self, base_currency: str = "USD") -> dict[str, Any]:
        """Get all rates for a base currency.

        Args:
            base_currency: Base currency code

        Returns:
            Dict mapping currency codes to rates
        """
        ...


class ForexSourceABC(DataSourceABC):
    """
    Abstract base class for forex data sources.

    Specializes DataSource for fetching currency exchange rates.
    Examples: Frankfurter, European Central Bank, Yahoo Finance.
    """

    @property
    def supported_markets(self) -> "list[Market]":
        """Forex sources only support the FOREX market."""
        from ..models import Market

        return [Market.FOREX]

    @abstractmethod
    async def get_rate(self, from_currency: str, to_currency: str) -> Optional["ExchangeRate"]:
        """
        Get exchange rate between two currencies.

        Args:
            from_currency: Source currency code (e.g., "USD").
            to_currency: Target currency code (e.g., "CNY").

        Returns:
            ExchangeRate object if successful, None if not available.
        """
        pass

    @abstractmethod
    async def get_all_rates(self, base_currency: str = "USD") -> dict[str, "ExchangeRate"]:
        """
        Get all rates for a base currency.

        Args:
            base_currency: Base currency code (e.g., "USD").

        Returns:
            Dictionary mapping currency codes to ExchangeRate objects.
        """
        pass


# =============================================================================
# GPR Source Interface
# =============================================================================


@runtime_checkable
class IGprSource(Protocol):
    """Protocol for Geopolitical Risk Index data sources."""

    @property
    def name(self) -> str:
        """Unique identifier for this data source."""
        ...

    @property
    def priority(self) -> int:
        """Priority level for source selection."""
        ...

    @property
    def supported_markets(self) -> "list[Market]":
        """List of markets this source can handle."""
        ...

    async def is_available(self) -> bool:
        """Check if the data source is currently available."""
        ...

    def get_gpr_history(self, months: int = 12) -> list[dict[str, Any]]:
        """Get GPR history data.

        Args:
            months: Number of months of history

        Returns:
            List of GPR data points
        """
        ...

    def get_gpr_analysis(self) -> dict[str, Any]:
        """Get GPR analysis with changes and risk level.

        Returns:
            Analysis dict with latest, horizons, and risk info
        """
        ...


class GprSourceABC(DataSourceABC):
    """
    Abstract base class for GPR data sources.

    Specializes DataSource for fetching Geopolitical Risk Index data.
    The GPR index measures geopolitical tension and risk levels globally.
    """

    @property
    def supported_markets(self) -> "list[Market]":
        """GPR sources only support the GLOBAL market."""
        from ..models import Market

        return [Market.GLOBAL]

    @abstractmethod
    def get_gpr_history(self, months: int = 12) -> list[dict[str, Any]]:
        """
        Get GPR history data.

        Args:
            months: Number of months of history to fetch (default 12).

        Returns:
            List of dictionaries, each containing:
            - date: str (YYYY-MM format)
            - value: float (GPR index value)
        """
        pass

    @abstractmethod
    def get_gpr_analysis(self) -> dict[str, Any]:
        """
        Get GPR analysis with changes and risk level.

        Returns:
            Dictionary containing:
            - latest: dict with date and value
            - horizons: dict with 1M, 3M, 6M, 1Y, 5Y, 10Y changes
            - risk: dict with level and color
        """
        pass


__all__ = [
    # Base
    "IDataSource",
    "DataSourceABC",
    # Quote
    "IQuoteSource",
    "QuoteSourceABC",
    # Gold
    "IGoldSource",
    "GoldSourceABC",
    # Forex
    "IForexSource",
    "ForexSourceABC",
    # GPR
    "IGprSource",
    "GprSourceABC",
]
