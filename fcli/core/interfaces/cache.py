"""Cache interface definitions."""

from abc import ABC, abstractmethod
from typing import Any, Protocol


class ICache(Protocol):
    """Cache interface - Protocol for type checking."""

    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, data: Any, ttl: int) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...
    async def async_get(self, key: str) -> Any | None: ...
    async def async_set(self, key: str, data: Any, ttl: int) -> None: ...
    async def async_delete(self, key: str) -> None: ...
    async def async_clear(self) -> None: ...


class CacheABC(ABC):
    """Cache abstract base class - for runtime enforcement."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, data: Any, ttl: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def async_get(self, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def async_set(self, key: str, data: Any, ttl: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def async_delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def async_clear(self) -> None:
        raise NotImplementedError
