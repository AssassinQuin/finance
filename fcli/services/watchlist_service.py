"""Watchlist service for managing user's tracked assets."""


from ..core.models import Asset, AssetType, Market
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

        assets_to_add = [self._code_to_asset(code) for code in codes]
        added = 0

        for asset in assets_to_add:
            if await storage.add(asset):
                added += 1
        return added

    async def remove_asset(self, code: str) -> bool:
        """Remove asset from watchlist. Returns True if removed."""
        return await storage.remove(code.upper())

    def _code_to_asset(self, code: str) -> Asset:
        """Convert user input code to Asset with inferred market/type."""
        code = code.strip()
        upper_code = code.upper()

        # Detect market and type from code pattern
        if upper_code.startswith(("SH", "SZ")) or code.isdigit() and len(code) == 6:
            # A股
            if code.isdigit() and len(code) == 6:
                prefix = code[:2]
                api_code = f"sh{code}" if prefix in ("60", "68") else f"sz{code}"
            else:
                api_code = code.lower()
            return Asset(
                code=code.upper(),
                api_code=api_code,
                name=code.upper(),
                market=Market.CN,
                type=AssetType.STOCK,
            )

        elif upper_code.startswith("HK") or code.isdigit() and len(code) == 5:
            # 港股
            api_code = f"rt_hk{code[-5:]}"
            return Asset(
                code=code.upper(),
                api_code=api_code,
                name=code.upper(),
                market=Market.HK,
                type=AssetType.STOCK,
            )

        elif code.isdigit() and len(code) == 6:
            # Could be A股 or fund, default to A股
            prefix = code[:2]
            api_code = f"sh{code}" if prefix in ("60", "68") else f"sz{code}"
            return Asset(
                code=code.upper(),
                api_code=api_code,
                name=code.upper(),
                market=Market.CN,
                type=AssetType.STOCK,
            )

        else:
            # Default: US stock or global index
            return Asset(
                code=code.upper(),
                api_code=code.lower(),
                name=code.upper(),
                market=Market.US,
                type=AssetType.STOCK,
            )


watchlist_service = WatchlistService()
