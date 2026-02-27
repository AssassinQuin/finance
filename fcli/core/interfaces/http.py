"""HTTP Client Abstract Interface.

Defines the contract for HTTP client implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class IHttpClient(Protocol):
    """Protocol for HTTP client implementations.

    Use Protocol for structural subtyping - allows any class with
    matching methods to be considered compatible without inheritance.
    """

    async def fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        text_mode: bool = False,
        binary_mode: bool = False,
        follow_redirects: bool = True,
        use_proxy: bool = True,
    ) -> Any:
        """Fetch data from URL.

        Args:
            url: Target URL
            params: Query parameters
            text_mode: Return text instead of JSON
            binary_mode: Return bytes
            follow_redirects: Follow HTTP redirects
            use_proxy: Use configured proxy

        Returns:
            JSON data, text, or bytes depending on mode
        """
        ...

    async def close(self) -> None:
        """Close the HTTP session and cleanup resources."""
        ...


class HttpClientABC(ABC):
    """Abstract base class for HTTP client implementations.

    Use ABC when you want explicit inheritance and need to enforce
    implementation of all methods.
    """

    @abstractmethod
    async def fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        text_mode: bool = False,
        binary_mode: bool = False,
        follow_redirects: bool = True,
        use_proxy: bool = True,
    ) -> Any:
        """Fetch data from URL.

        Args:
            url: Target URL
            params: Query parameters
            text_mode: Return text instead of JSON
            binary_mode: Return bytes
            follow_redirects: Follow HTTP redirects
            use_proxy: Use configured proxy

        Returns:
            JSON data, text, or bytes depending on mode
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the HTTP session and cleanup resources."""
        pass


__all__ = ["IHttpClient", "HttpClientABC"]
