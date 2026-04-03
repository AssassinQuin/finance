"""Storage Abstract Interface.

Defines the contract for storage implementations.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Asset


class StorageABC(ABC):
    """Abstract base class for storage implementations."""

    @abstractmethod
    async def load(self) -> "list[Asset]":
        pass

    @abstractmethod
    async def save(self, assets: "list[Asset]") -> None:
        pass

    @abstractmethod
    async def add(self, asset: "Asset") -> bool:
        pass

    @abstractmethod
    async def remove(self, code: str) -> bool:
        pass

    @abstractmethod
    async def get(self, code: str) -> "Asset | None":
        pass

    @abstractmethod
    async def clear(self) -> int:
        pass


__all__ = ["StorageABC"]
