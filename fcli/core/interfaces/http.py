"""HTTP Client Abstract Interface."""

from abc import ABC, abstractmethod
from typing import Any


class HttpClientABC(ABC):
    """Abstract base class for HTTP client implementations."""

    @abstractmethod
    async def fetch(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        text_mode: bool = False,
        binary_mode: bool = False,
        follow_redirects: bool = True,
        use_proxy: bool = True,
    ) -> Any:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


__all__ = ["HttpClientABC"]
