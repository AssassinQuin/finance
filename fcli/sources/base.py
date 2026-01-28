from abc import ABC, abstractmethod
from typing import List

from ..core.models import Asset, Quote


class QuoteSource(ABC):
    """Abstract base class for quote sources."""

    @abstractmethod
    async def fetch(self, assets: List[Asset]) -> List[Quote]:
        """Fetch quotes for a list of assets."""
        pass
