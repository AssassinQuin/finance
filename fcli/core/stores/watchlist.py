import json
from typing import List, Dict, Optional
from datetime import datetime
import aiomysql

from ..database import Database
from ..models import WatchlistAssetDB, Asset, Market, AssetType
from .base import BaseStore


class WatchlistAssetStore(BaseStore[WatchlistAssetDB]):
    """Store for watchlist assets."""

    table_name = "watchlist_assets"
    model_class = WatchlistAssetDB

    @classmethod
    def _row_to_model(cls, row: Dict) -> WatchlistAssetDB:
        return WatchlistAssetDB(
            id=row.get("id"),
            code=row.get("code", ""),
            api_code=row.get("api_code", ""),
            name=row.get("name", ""),
            market=row.get("market", ""),
            type=row.get("type", ""),
            extra=json.loads(row.get("extra")) if isinstance(row.get("extra"), str) else (row.get("extra") or {}),
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
            market=Market(db_asset.market) if db_asset.market else Market.CN,
            type=AssetType(db_asset.type) if db_asset.type else AssetType.STOCK,
            added_at=db_asset.added_at or datetime.now(),
            extra=db_asset.extra,
        )

    @classmethod
    def _asset_to_db(cls, asset: Asset) -> WatchlistAssetDB:
        """Convert Asset model to DB model."""
        return WatchlistAssetDB(
            code=asset.code,
            api_code=asset.api_code,
            name=asset.name,
            market=asset.market.value,
            type=asset.type.value,
            extra=asset.extra,
            is_active=True,
            added_at=asset.added_at,
        )

    @classmethod
    async def get_all_active(cls) -> List[WatchlistAssetDB]:
        """Get all active watchlist assets."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT * FROM watchlist_assets
        WHERE is_active = TRUE
        ORDER BY added_at
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_by_code(cls, code: str) -> Optional[WatchlistAssetDB]:
        """Get asset by code."""
        if not cls._is_enabled():
            return None

        sql = "SELECT * FROM watchlist_assets WHERE code = %s"

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (code,))
                row = await cur.fetchone()
                return cls._row_to_model(row) if row else None

    @classmethod
    async def add(cls, asset: Asset) -> bool:
        """Add or update an asset in watchlist."""
        if not cls._is_enabled():
            return False

        db_asset = cls._asset_to_db(asset)

        sql = """
        INSERT INTO watchlist_assets
            (code, api_code, name, market, type, extra, is_active, added_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            api_code = VALUES(api_code),
            name = VALUES(name),
            market = VALUES(market),
            type = VALUES(type),
            extra = VALUES(extra),
            is_active = TRUE,
            updated_at = NOW()
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    sql,
                    (
                        db_asset.code,
                        db_asset.api_code,
                        db_asset.name,
                        db_asset.market,
                        db_asset.type,
                        db_asset.extra if isinstance(db_asset.extra, str) else json.dumps(db_asset.extra or {}),
                        db_asset.is_active,
                        db_asset.added_at or datetime.now(),
                    ),
                )
                return True

    @classmethod
    async def remove(cls, code: str) -> bool:
        """Remove an asset from watchlist (soft delete)."""
        if not cls._is_enabled():
            return False

        sql = """
        UPDATE watchlist_assets
        SET is_active = FALSE, updated_at = NOW()
        WHERE code = %s
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (code,))
                return cur.rowcount > 0

    @classmethod
    async def hard_delete(cls, code: str) -> bool:
        """Permanently delete an asset from watchlist."""
        if not cls._is_enabled():
            return False

        sql = "DELETE FROM watchlist_assets WHERE code = %s"

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (code,))
                return cur.rowcount > 0

    @classmethod
    async def get_assets(cls) -> List[Asset]:
        """Get all active assets as Asset models (for compatibility)."""
        db_assets = await cls.get_all_active()
        return [cls._db_to_asset(db_asset) for db_asset in db_assets]
