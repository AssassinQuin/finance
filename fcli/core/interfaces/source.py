"""Data Source Abstract Interfaces.

Defines contracts for data source services (Quote, Gold, Forex, GPR).
All specialized sources inherit from the base DataSourceABC class.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..models import Asset, ExchangeRate, Market, Quote


class DataSourceABC(ABC):
    """Abstract base class for all data sources.

    Attributes:
        name: Unique identifier for this data source (e.g., "sina", "eastmoney").
        priority: Priority level for source selection (higher = preferred).
        supported_markets: List of markets this source can handle.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        pass

    @property
    @abstractmethod
    def supported_markets(self) -> "list[Market]":
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass


class QuoteSourceABC(DataSourceABC):
    """Abstract base class for stock/fund quote sources."""

    @abstractmethod
    async def fetch_single(self, asset: "Asset") -> "Quote | None":
        pass

    @abstractmethod
    async def fetch_all(self, assets: "list[Asset]") -> "list[Quote]":
        pass


class GoldSourceABC(DataSourceABC):
    """Abstract base class for gold reserve data sources."""

    @property
    def supported_markets(self) -> "list[Market]":
        from ..models import Market

        return [Market.GLOBAL]

    @abstractmethod
    async def get_latest(self, country_codes: list[str] | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def get_history(self, country_code: str, months: int = 120) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class ForexSourceABC(DataSourceABC):
    """Abstract base class for forex data sources."""

    @property
    def supported_markets(self) -> "list[Market]":
        from ..models import Market

        return [Market.GLOBAL]

    @abstractmethod
    async def get_rate(self, base_currency: str, quote_currency: str) -> Optional["ExchangeRate"]:
        pass

    @abstractmethod
    async def get_all_rates(self, base_currency: str = "USD") -> dict[str, "ExchangeRate"]:
        pass


class GprSourceABC(DataSourceABC):
    """Abstract base class for GPR data sources."""

    @property
    def supported_markets(self) -> "list[Market]":
        from ..models import Market

        return [Market.GLOBAL]

    @abstractmethod
    def get_gpr_history(self, months: int = 12) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def get_gpr_analysis(self) -> dict[str, Any]:
        pass


__all__ = [
    "DataSourceABC",
    "QuoteSourceABC",
    "GoldSourceABC",
    "ForexSourceABC",
    "GprSourceABC",
]
