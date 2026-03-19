"""Watchlist service for managing user's tracked assets."""

from ..core.factories import AssetFactory
from ..core.models import Asset
from ..core.storage import storage


class WatchlistService:
    """Service for managing watchlist assets with DB and JSON fallback."""

    async def list_assets(self) -> list[Asset]:
        """List all active assets in watchlist."""
        return await storage.load()

    async def add_assets(self, codes: list[str]) -> int:
        """Add assets to watchlist. Returns count added."""
        if not codes:
            return 0

        assets_to_add = [AssetFactory.from_code(code) for code in codes]
        added = 0

        for asset in assets_to_add:
            if await storage.add(asset):
                added += 1
        return added

    async def remove_asset(self, code: str) -> bool:
        """Remove asset from watchlist. Returns True if removed."""
        return await storage.remove(code.upper())

    async def remove_assets(self, codes: list[str]) -> int:
        """Remove multiple assets from watchlist. Returns count removed."""
        if not codes:
            return 0
        removed = 0
        for code in codes:
            if await storage.remove(code.upper()):
                removed += 1
        return removed


watchlist_service = WatchlistService()
