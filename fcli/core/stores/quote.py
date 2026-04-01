"""Quote store - flat table implementation."""

from datetime import datetime, timezone

from ...core.database import Database
from ..models.asset import Quote
from ..models.base import Market


class QuoteStore:
    """Store for quote data using flat quotes table."""

    table_name = "quotes"

    @classmethod
    async def save(cls, quote: Quote) -> bool:
        """Save quote data to quotes table."""
        if not Database.is_enabled():
            return False

        try:
            asset_type = (
                "fund" if quote.type and hasattr(quote.type, "value") and quote.type.value == "fund" else "stock"
            )
            now = datetime.now(timezone.utc)

            await Database.execute(
                """
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
                """,
                quote.code,
                quote.name,
                asset_type,
                quote.price,
                quote.change_percent,
                quote.high,
                quote.low,
                int(quote.volume) if quote.volume and quote.volume.isdigit() else None,
                quote.update_time or now,
                "Akshare",
                now,
            )
            return True
        except Exception:
            return False

    @classmethod
    async def save_many(cls, quotes: list[Quote]) -> int:
        """Save multiple quotes using execute_many."""
        if not Database.is_enabled() or not quotes:
            return 0

        try:
            now = datetime.now(timezone.utc)
            args_list = []
            for quote in quotes:
                asset_type = (
                    "fund" if quote.type and hasattr(quote.type, "value") and quote.type.value == "fund" else "stock"
                )
                args_list.append(
                    (
                        quote.code,
                        quote.name,
                        asset_type,
                        quote.price,
                        quote.change_percent,
                        quote.high,
                        quote.low,
                        int(quote.volume) if quote.volume and quote.volume.isdigit() else None,
                        quote.update_time or now,
                        "Akshare",
                        now,
                    )
                )

            await Database.execute_many(
                """
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
                """,
                args_list,
            )
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
            code=row["code"],
            name=row["name"] or "",
            price=float(row["price"]) if row["price"] else 0.0,
            change_percent=float(row["change_percent"]) if row["change_percent"] else 0.0,
            update_time=row["quote_time"] or datetime.now(),
            market=Market.CN,
            high=float(row["high_price"]) if row["high_price"] else None,
            low=float(row["low_price"]) if row["low_price"] else None,
            volume=str(row["volume"]) if row["volume"] else None,
        )

