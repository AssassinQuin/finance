"""Data Source Abstract Interfaces.

Defines contracts for data source services.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Asset, Market, Quote


class DataSourceABC(ABC):
    """Abstract base class for all data sources."""

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


__all__ = [
    "DataSourceABC",
    "QuoteSourceABC",
]
