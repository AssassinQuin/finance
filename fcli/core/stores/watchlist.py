import json

from ...utils.time_util import utcnow
from ..database import Database
from ..models import Asset, AssetType, Market, WatchlistAssetDB


class WatchlistAssetStore:

    def _row_to_model(self, row: dict) -> WatchlistAssetDB:
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

    def _db_to_asset(self, db_asset: WatchlistAssetDB) -> Asset:
        return Asset(
            code=db_asset.code,
            api_code=db_asset.api_code,
            name=db_asset.name,
            market=db_asset.market,
            type=db_asset.type,
            added_at=db_asset.added_at or utcnow(),
            extra=db_asset.extra,
        )

    def _asset_to_db(self, asset: Asset) -> WatchlistAssetDB:
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

    async def get_all_active(self) -> list[WatchlistAssetDB]:
        if not Database.is_enabled():
            return []

        sql = """
        SELECT * FROM watchlist_assets
        WHERE is_active = TRUE
        ORDER BY added_at
        """

        rows = await Database.fetch_all(sql)
        return [self._row_to_model(dict(row)) for row in rows]

    async def get_by_code(self, code: str) -> WatchlistAssetDB | None:
        if not Database.is_enabled():
            return None

        sql = "SELECT * FROM watchlist_assets WHERE code = $1"

        row = await Database.fetch_one(sql, code)
        return self._row_to_model(dict(row)) if row else None

    async def add(self, asset: Asset) -> bool:
        if not Database.is_enabled():
            return False

        db_asset = self._asset_to_db(asset)

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

    async def remove(self, code: str) -> bool:
        if not Database.is_enabled():
            return False

        sql = """
        UPDATE watchlist_assets
        SET is_active = FALSE, updated_at = NOW()
        WHERE code = $1
        """

        result = await Database.execute(sql, code)
        return result != "UPDATE 0"

    async def hard_delete(self, code: str) -> bool:
        if not Database.is_enabled():
            return False

        sql = "DELETE FROM watchlist_assets WHERE code = $1"

        result = await Database.execute(sql, code)
        return result != "DELETE 0"

    async def get_assets(self) -> list[Asset]:
        db_assets = await self.get_all_active()
        return [self._db_to_asset(db_asset) for db_asset in db_assets]

    async def clear_all(self) -> int:
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


watchlist_asset_store = WatchlistAssetStore()
