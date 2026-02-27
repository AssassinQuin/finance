"""Storage layer - database only."""

from typing import List, Optional

from .config import config
from .database import Database
from .models import Asset
from .stores import WatchlistAssetStore


class Storage:
    """Database-only storage for watchlist assets."""

    _initialized = False

    async def _ensure_db(self):
        """Ensure database is initialized."""
        if not Storage._initialized:
            await Database.init(config)
            Storage._initialized = True

    async def load(self) -> List[Asset]:
        """Load all active assets from database."""
        await self._ensure_db()
        if not Database.is_enabled():
            return []
        return await WatchlistAssetStore.get_assets()

    async def save(self, assets: List[Asset]):
        """Save assets to database."""
        await self._ensure_db()
        if not Database.is_enabled():
            return
        for asset in assets:
            await WatchlistAssetStore.add(asset)

    async def add(self, asset: Asset) -> bool:
        """Add asset to watchlist."""
        await self._ensure_db()
        if not Database.is_enabled():
            return False
        return await WatchlistAssetStore.add(asset)

    async def remove(self, code: str) -> bool:
        """Remove asset from watchlist."""
        await self._ensure_db()
        if not Database.is_enabled():
            return False
        return await WatchlistAssetStore.remove(code)

    async def get(self, code: str) -> Optional[Asset]:
        """Get asset by code."""
        await self._ensure_db()
        if not Database.is_enabled():
            return None
        return await WatchlistAssetStore.get_by_code(code)


storage = Storage()
