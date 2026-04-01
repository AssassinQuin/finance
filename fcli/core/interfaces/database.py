"""Database interface definitions."""

from abc import ABC, abstractmethod
from typing import Any


class DatabaseABC(ABC):
    """Abstract base class for database implementations."""

    @abstractmethod
    async def execute(self, sql: str, *args: Any) -> int:
        pass

    @abstractmethod
    async def fetch_one(self, sql: str, *args: Any) -> dict | None:
        pass

    @abstractmethod
    async def fetch_all(self, sql: str, *args: Any) -> list[dict]:
        pass

    @abstractmethod
    async def fetchval(self, sql: str, *args: Any) -> Any:
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        pass


__all__ = ["DatabaseABC"]
