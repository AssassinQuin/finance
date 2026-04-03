"""Data Source Abstract Interfaces.

Defines contracts for data source services.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Asset, ExchangeRate, Quote


class DataSourceABC(ABC):
    """Abstract base class for all data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
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


class ForexSourceABC(DataSourceABC):
    """Abstract base class for forex rate sources."""

    @abstractmethod
    async def fetch_rate(self, base_currency: str, quote_currency: str) -> "ExchangeRate | None":
        pass


__all__ = [
    "DataSourceABC",
    "ForexSourceABC",
    "QuoteSourceABC",
]
