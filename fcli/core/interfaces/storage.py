"""Storage Abstract Interface.

Defines the contract for storage implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol, TYPE_CHECKING, runtime_checkable

# Forward references to avoid circular imports
# These are just type hints - actual imports happen at runtime in implementations
if TYPE_CHECKING:
    from ..models import Asset


@runtime_checkable
class IStorage(Protocol):
    """Protocol for storage implementations.

    Provides watchlist asset persistence.
    """

    async def load(self) -> "List[Asset]":
        """Load all active assets from storage.

        Returns:
            List of Asset objects
        """
        ...

    async def save(self, assets: "List[Asset]") -> None:
        """Save assets to storage.

        Args:
            assets: List of assets to save
        """
        ...

    async def add(self, asset: "Asset") -> bool:
        """Add asset to storage.

        Args:
            asset: Asset to add

        Returns:
            True if added successfully
        """
        ...

    async def remove(self, code: str) -> bool:
        """Remove asset from storage.

        Args:
            code: Asset code to remove

        Returns:
            True if removed successfully
        """
        ...

    async def get(self, code: str) -> "Optional[Asset]":
        """Get asset by code.

        Args:
            code: Asset code

        Returns:
            Asset if found, None otherwise
        """
        ...


class StorageABC(ABC):
    """Abstract base class for storage implementations."""

    @abstractmethod
    async def load(self) -> "List[Asset]":
        """Load all active assets from storage."""
        pass

    @abstractmethod
    async def save(self, assets: "List[Asset]") -> None:
        """Save assets to storage."""
        pass

    @abstractmethod
    async def add(self, asset: "Asset") -> bool:
        """Add asset to storage."""
        pass

    @abstractmethod
    async def remove(self, code: str) -> bool:
        """Remove asset from storage."""
        pass

    @abstractmethod
    async def get(self, code: str) -> "Optional[Asset]":
        """Get asset by code."""
        pass
