import json
from datetime import datetime

from ..database import Database
from ..models import Asset, AssetType, Market, WatchlistAssetDB
from ...utils.time_util import utcnow


class WatchlistAssetStore:
    """Store for watchlist assets."""

    @classmethod
    def _row_to_model(cls, row: dict) -> WatchlistAssetDB:
        extra_data = row.get("extra")
        if isinstance(extra_data, str):
            extra_data = json.loads(extra_data)
        elif extra_data is None:
            extra_data = {}

        market_val = row.get("market", "")
        type_val = row.get("type", "")
        return WatchlistAssetDB(
            id=row.get("id"),
            code=row.get("code", ""),
            api_code=row.get("api_code", ""),
            name=row.get("name", ""),
            market=Market(market_val) if market_val else Market.CN,
            type=AssetType(type_val) if type_val else AssetType.STOCK,
            extra=extra_data,
            is_active=bool(row.get("is_active", True)),
            added_at=row.get("added_at"),
            updated_at=row.get("updated_at"),
        )

    @classmethod
    def _db_to_asset(cls, db_asset: WatchlistAssetDB) -> Asset:
        """Convert DB model to Asset model."""
        return Asset(
            code=db_asset.code,
            api_code=db_asset.api_code,
            name=db_asset.name,
            market=db_asset.market,
            type=db_asset.type,
            added_at=db_asset.added_at or utcnow(),
            extra=db_asset.extra,
        )

    @classmethod
    def _asset_to_db(cls, asset: Asset) -> WatchlistAssetDB:
        """Convert Asset model to DB model."""
        return WatchlistAssetDB(
            code=asset.code,
            api_code=asset.api_code,
            name=asset.name,
            market=asset.market,
            type=asset.type,
            extra=asset.extra,
            is_active=True,
            added_at=asset.added_at,
        )

    @classmethod
    async def get_all_active(cls) -> list[WatchlistAssetDB]:
        """Get all active watchlist assets."""
        if not Database.is_enabled():
            return []

        sql = """
        SELECT * FROM watchlist_assets
        WHERE is_active = TRUE
        ORDER BY added_at
        """

        rows = await Database.fetch_all(sql)
        return [cls._row_to_model(dict(row)) for row in rows]

    @classmethod
    async def get_by_code(cls, code: str) -> WatchlistAssetDB | None:
        """Get asset by code."""
        if not Database.is_enabled():
            return None

        sql = "SELECT * FROM watchlist_assets WHERE code = $1"

        row = await Database.fetch_one(sql, code)
        return cls._row_to_model(dict(row)) if row else None

    @classmethod
    async def add(cls, asset: Asset) -> bool:
        """Add or update an asset in watchlist."""
        if not Database.is_enabled():
            return False

        db_asset = cls._asset_to_db(asset)

        sql = """
        INSERT INTO watchlist_assets
            (code, api_code, name, market, type, extra, is_active, added_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (code) DO UPDATE SET
            api_code = EXCLUDED.api_code,
            name = EXCLUDED.name,
            market = EXCLUDED.market,
            type = EXCLUDED.type,
            extra = EXCLUDED.extra,
            is_active = TRUE,
            updated_at = NOW()
        """

        await Database.execute(
            sql,
            db_asset.code,
            db_asset.api_code,
            db_asset.name,
            db_asset.market,
            db_asset.type,
            db_asset.extra or {},
            db_asset.is_active,
            db_asset.added_at or utcnow(),
        )
        return True

    @classmethod
    async def remove(cls, code: str) -> bool:
        """Remove an asset from watchlist (soft delete)."""
        if not Database.is_enabled():
            return False

        sql = """
        UPDATE watchlist_assets
        SET is_active = FALSE, updated_at = NOW()
        WHERE code = $1
        """

        result = await Database.execute(sql, code)
        return result != "UPDATE 0"

    @classmethod
    async def hard_delete(cls, code: str) -> bool:
        """Permanently delete an asset from watchlist."""
        if not Database.is_enabled():
            return False

        sql = "DELETE FROM watchlist_assets WHERE code = $1"

        result = await Database.execute(sql, code)
        return result != "DELETE 0"

    @classmethod
    async def get_assets(cls) -> list[Asset]:
        """Get all active assets as Asset models."""
        db_assets = await cls.get_all_active()
        return [cls._db_to_asset(db_asset) for db_asset in db_assets]

    @classmethod
    async def clear_all(cls) -> int:
        """Deactivate all watchlist assets. Returns count deactivated."""
        if not Database.is_enabled():
            return 0

        sql = """
        UPDATE watchlist_assets
        SET is_active = FALSE, updated_at = NOW()
        WHERE is_active = TRUE
        """

        result = await Database.execute(sql)
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0
