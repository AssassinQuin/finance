"""Quote store - PostgreSQL implementation."""

from datetime import datetime
from typing import Any, Optional

from ..database import Database
from ..models.asset import Quote
from ..models.base import Market, AssetType
from .base import BaseStore


class QuoteStore(BaseStore[Quote]):
    """Store for quote data using PostgreSQL."""

    table_name = "quotes"

    @classmethod
    async def save(cls, quote: Quote) -> bool:
        """Save quote data using PostgreSQL UPSERT."""
        if not Database.is_enabled():
            return False

        try:
            await Database.execute(
                f"""
                INSERT INTO {cls.table_name} (
                    code, name, price, change_percent, high, low, volume,
                    market, quote_time
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (code, DATE(quote_time)) DO UPDATE SET
                    name = EXCLUDED.name,
                    price = EXCLUDED.price,
                    change_percent = EXCLUDED.change_percent,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    volume = EXCLUDED.volume,
                    market = EXCLUDED.market,
                    quote_time = EXCLUDED.quote_time,
                    updated_at = CURRENT_TIMESTAMP
                """,
                quote.code,
                quote.name,
                quote.price,
                quote.change_percent,
                quote.high,
                quote.low,
                quote.volume,
                quote.market.value if isinstance(quote.market, Market) else quote.market,
                quote.update_time,
            )
            return True
        except Exception:
            return False

    @classmethod
    async def save_many(cls, quotes: list[Quote]) -> int:
        """Save multiple quotes."""
        if not Database.is_enabled():
            return 0

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

        rows = await Database.fetch_all(
            f"""
            SELECT code, name, price, change_percent, high, low, volume,
                   market, quote_time
            FROM {cls.table_name}
            WHERE code = $1
            ORDER BY quote_time DESC
            LIMIT $2
            """,
            code,
            limit,
        )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_latest(cls, code: str) -> Optional[Quote]:
        """Get latest quote for a code."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            f"""
            SELECT code, name, price, change_percent, high, low, volume,
                   market, quote_time
            FROM {cls.table_name}
            WHERE code = $1
            ORDER BY quote_time DESC
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
    def _row_to_model(cls, row: Any) -> Quote:
        return Quote(
            code=row["code"],
            name=row["name"] or "",
            price=float(row["price"]) if row["price"] else 0.0,
            change_percent=float(row["change_percent"]) if row["change_percent"] else 0.0,
            update_time=row["quote_time"] or datetime.now(),
            market=Market(row["market"]) if row["market"] else Market.CN,
            type=AssetType.STOCK,
            high=float(row["high"]) if row["high"] else None,
            low=float(row["low"]) if row["low"] else None,
            volume=str(row["volume"]) if row["volume"] else None,
        )
