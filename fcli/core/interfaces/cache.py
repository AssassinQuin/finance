"""Cache Abstract Interface."""

from abc import ABC, abstractmethod
from typing import Any


class CacheABC(ABC):
    """Abstract base class for cache implementations."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    async def async_get(self, key: str) -> Any | None:
        pass

    @abstractmethod
    async def async_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        pass

    @abstractmethod
    async def async_delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def async_clear(self) -> None:
        pass


__all__ = ["CacheABC"]
