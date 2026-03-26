"""Quote fact store - V2 fact table implementation."""

from datetime import datetime, timezone

from ..database import Database
from ..models.asset import Quote
from ..models.base import Market
from .base import BaseStore


class QuoteFactStore(BaseStore[Quote]):
    """Store for quote data using V2 fact table (fact_quote + dim_asset)."""

    table_name = "fact_quote"

    @classmethod
    async def _get_or_create_asset_id(cls, code: str, name: str = "", asset_type: str = "stock") -> int | None:
        """Get or create asset_id from dim_asset."""
        if not Database.is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM dim_asset WHERE asset_code = $1",
                code,
            )
            if row:
                return row["id"]

            await conn.execute(
                """
                INSERT INTO dim_asset (asset_code, asset_name, asset_type)
                VALUES ($1, $2, $3)
                """,
                code,
                name or code,
                asset_type,
            )
            row = await conn.fetchrow(
                "SELECT id FROM dim_asset WHERE asset_code = $1",
                code,
            )
            return row["id"] if row else None

    @classmethod
    async def _get_source_id(cls, source_name: str = "Akshare") -> int | None:
        """Get source_id from dim_data_source."""
        if not Database.is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM dim_data_source WHERE source_name = $1",
                source_name,
            )
            return row["id"] if row else None

    @classmethod
    async def save(cls, quote: Quote) -> bool:
        """Save quote data to fact_quote table."""
        if not Database.is_enabled():
            return False

        pool = cls._pool()
        if not pool:
            return False

        try:
            asset_type = "fund" if quote.type and hasattr(quote.type, "value") and quote.type.value == "fund" else "stock"
            asset_id = await cls._get_or_create_asset_id(quote.code, quote.name, asset_type)
            if not asset_id:
                return False

            source_id = await cls._get_source_id("Akshare")
            now = datetime.now(timezone.utc)

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO fact_quote (
                        asset_id, quote_time, price, change_amount, change_percent,
                        open_price, high_price, low_price, prev_close, volume,
                        source_id, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (asset_id, DATE(quote_time)) DO UPDATE SET
                        price = EXCLUDED.price,
                        change_amount = EXCLUDED.change_amount,
                        change_percent = EXCLUDED.change_percent,
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        prev_close = EXCLUDED.prev_close,
                        volume = EXCLUDED.volume,
                        source_id = EXCLUDED.source_id
                    """,
                    asset_id,
                    quote.update_time or now,
                    quote.price,
                    None,
                    quote.change_percent,
                    None,
                    quote.high,
                    quote.low,
                    None,
                    int(quote.volume) if quote.volume and quote.volume.isdigit() else None,
                    source_id,
                    now,
                )
            return True
        except Exception:
            return False

    @classmethod
    async def save_many(cls, quotes: list[Quote]) -> int:
        """Save multiple quotes."""
        count = 0
        for quote in quotes:
            if await cls.save(quote):
                count += 1
        return count

    @classmethod
    async def get_by_code(cls, code: str, limit: int = 10) -> list[Quote]:
        """Get historical quotes for a code."""
        if not Database.is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.asset_code, a.asset_name, f.price, f.change_percent,
                       f.high_price, f.low_price, f.volume, f.quote_time
                FROM fact_quote f
                JOIN dim_asset a ON f.asset_id = a.id
                WHERE a.asset_code = $1
                ORDER BY f.quote_time DESC
                LIMIT $2
                """,
                code,
                limit,
            )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_latest(cls, code: str) -> Quote | None:
        """Get latest quote for a code."""
        if not Database.is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT a.asset_code, a.asset_name, f.price, f.change_percent,
                       f.high_price, f.low_price, f.volume, f.quote_time
                FROM fact_quote f
                JOIN dim_asset a ON f.asset_id = a.id
                WHERE a.asset_code = $1
                ORDER BY f.quote_time DESC
                LIMIT 1
                """,
                code,
            )

        if not row:
            return None

        return cls._row_to_model(row)

    @classmethod
    async def delete_old(cls, days: int = 30) -> int:
        """Delete quotes older than specified days."""
        if not Database.is_enabled():
            return 0

        result = await Database.execute(
            f"""
            DELETE FROM {cls.table_name}
            WHERE quote_time < CURRENT_DATE - INTERVAL '{days} days'
            """
        )
        return result or 0

    @classmethod
    def _row_to_model(cls, row) -> Quote:
        return Quote(
            code=row["asset_code"],
            name=row["asset_name"] or "",
            price=float(row["price"]) if row["price"] else 0.0,
            change_percent=float(row["change_percent"]) if row["change_percent"] else 0.0,
            update_time=row["quote_time"] or datetime.now(),
            market=Market.CN,
            high=float(row["high_price"]) if row["high_price"] else None,
            low=float(row["low_price"]) if row["low_price"] else None,
            volume=str(row["volume"]) if row["volume"] else None,
        )
