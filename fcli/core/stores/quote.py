"""Quote store - flat table implementation."""

from datetime import datetime, timezone

from ...core.database import Database
from ...utils.time_util import utcnow
from ..models.asset import Quote
from ..models.base import Market


class QuoteStore:
    """Store for quote data using flat quotes table."""

    table_name = "quotes"

    _UPSERT_SQL = """
        INSERT INTO quotes (
            code, name, asset_type, price, change_percent,
            high_price, low_price, volume, quote_time, data_source, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (code, DATE(quote_time)) DO UPDATE SET
            price = EXCLUDED.price,
            change_percent = EXCLUDED.change_percent,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            volume = EXCLUDED.volume
    """

    @classmethod
    def _quote_to_args(cls, quote: Quote, now: datetime, source: str = "Akshare") -> tuple:
        asset_type = "fund" if quote.type and hasattr(quote.type, "value") and quote.type.value == "fund" else "stock"
        return (
            quote.code,
            quote.name,
            asset_type,
            quote.price,
            quote.change_percent,
            quote.high,
            quote.low,
            int(quote.volume) if quote.volume and quote.volume.isdigit() else None,
            quote.update_time or now,
            source,
            now,
        )

    @classmethod
    async def save(cls, quote: Quote, source: str = "Akshare") -> bool:
        if not Database.is_enabled():
            return False

        try:
            now = datetime.now(timezone.utc)
            await Database.execute(cls._UPSERT_SQL, *cls._quote_to_args(quote, now, source))
            return True
        except Exception:
            return False

    @classmethod
    async def save_many(cls, quotes: list[Quote], source: str = "Akshare") -> int:
        if not Database.is_enabled() or not quotes:
            return 0

        try:
            now = datetime.now(timezone.utc)
            args_list = [cls._quote_to_args(q, now, source) for q in quotes]
            await Database.execute_many(cls._UPSERT_SQL, args_list)
            return len(args_list)
        except Exception:
            return 0

    @classmethod
    async def get_by_code(cls, code: str, limit: int = 10) -> list[Quote]:
        """Get historical quotes for a code."""
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT code, name, price, change_percent,
                   high_price, low_price, volume, quote_time
            FROM quotes
            WHERE code = $1
            ORDER BY quote_time DESC
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

        row = await Database.fetch_one(
            """
            SELECT code, name, price, change_percent,
                   high_price, low_price, volume, quote_time
            FROM quotes
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
        if not Database.is_enabled():
            return 0

        result = await Database.execute(
            """
            DELETE FROM quotes
            WHERE quote_time < CURRENT_DATE - $1::int * INTERVAL '1 day'
            """,
            days,
        )
        return result or 0

    @classmethod
    def _row_to_model(cls, row) -> Quote:
        return Quote(
            code=row["code"],
            name=row["name"] or "",
            price=float(row["price"]) if row["price"] else 0.0,
            change_percent=float(row["change_percent"]) if row["change_percent"] else 0.0,
            update_time=row["quote_time"] or utcnow(),
            market=Market.CN,
            high=float(row["high_price"]) if row["high_price"] else None,
            low=float(row["low_price"]) if row["low_price"] else None,
            volume=str(row["volume"]) if row["volume"] else None,
        )
