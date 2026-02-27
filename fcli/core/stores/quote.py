"""Quote store for database operations."""

from typing import List, Dict, Optional
from datetime import date, datetime
import aiomysql

from ..database import Database
from ..models import Quote
from .base import BaseStore


class QuoteStore(BaseStore[Quote]):
    """Store for quote data."""

    table_name = "quotes"
    model_class = Quote
    pk_field = "id"

    @classmethod
    def _row_to_model(cls, row: Dict) -> Quote:
        return Quote(
            code=row.get("symbol", ""),
            name=row.get("name", ""),
            price=float(row.get("price", 0)),
            change_percent=float(row.get("change_pct", 0)),
            update_time=row.get("quote_time").isoformat() if row.get("quote_time") else "",
            market=row.get("exchange", ""),
            type=row.get("type", "stock"),
            volume=str(row.get("volume", "")),
            extra=row.get("extra_data") or {},
        )

    @classmethod
    async def save(cls, quote: Quote, quote_date: date = None) -> bool:
        """Save a quote (upsert)."""
        if not cls._is_enabled():
            return False

        q_date = quote_date or date.today()

        sql = """
        INSERT INTO quotes
            (symbol, name, type, exchange, price, change_pct, volume,
             quote_date, quote_time, data_source, extra_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            price = VALUES(price),
            change_pct = VALUES(change_pct),
            volume = VALUES(volume),
            quote_time = VALUES(quote_time),
            extra_data = VALUES(extra_data),
            updated_at = NOW()
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    sql,
                    (
                        quote.code,
                        quote.name,
                        quote.type.value if hasattr(quote.type, "value") else quote.type,
                        quote.market.value if hasattr(quote.market, "value") else quote.market,
                        quote.price,
                        quote.change_percent,
                        int(quote.volume) if quote.volume and quote.volume.isdigit() else None,
                        q_date,
                        datetime.now(),
                        "fcli",
                        quote.extra,
                    ),
                )
                return True

    @classmethod
    async def save_batch(cls, quotes: List[Quote], quote_date: date = None) -> int:
        """Batch save quotes."""
        if not cls._is_enabled() or not quotes:
            return 0

        q_date = quote_date or date.today()
        count = 0
        for quote in quotes:
            if await cls.save(quote, q_date):
                count += 1
        return count

    @classmethod
    async def get_latest_by_symbol(cls, symbol: str) -> Optional[Quote]:
        """Get latest quote for a symbol."""
        if not cls._is_enabled():
            return None

        sql = """
        SELECT * FROM quotes
        WHERE symbol = %s
        ORDER BY quote_date DESC, quote_time DESC
        LIMIT 1
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (symbol,))
                row = await cur.fetchone()
                return cls._row_to_model(row) if row else None

    @classmethod
    async def get_history(cls, symbol: str, days: int = 30) -> List[Quote]:
        """Get historical quotes for a symbol."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT * FROM quotes
        WHERE symbol = %s
        ORDER BY quote_date DESC
        LIMIT %s
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (symbol, days))
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]
