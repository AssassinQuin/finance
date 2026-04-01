"""Cache Abstract Interface."""

from abc import ABC, abstractmethod
from typing import Any


class CacheABC(ABC):
    """Abstract base class for cache implementations.

    Subclasses must implement async methods. Sync methods are optional;
    they raise NotImplementedError by default for pure-async backends (e.g. PostgresCache).
    """

    def get(self, key: str) -> Any | None:
        raise NotImplementedError(f"{type(self).__name__} does not support sync get, use async_get instead")

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support sync set, use async_set instead")

    def delete(self, key: str) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support sync delete, use async_delete instead")

    def clear(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support sync clear, use async_clear instead")

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
