"""Exchange rate store for database operations."""

from typing import List, Dict, Optional
from datetime import date
import aiomysql

from ..database import Database
from ..models import ExchangeRate
from .base import BaseStore


class ExchangeRateStore(BaseStore[ExchangeRate]):
    """Store for exchange rate data."""

    table_name = "exchange_rates"
    model_class = ExchangeRate

    @classmethod
    def _row_to_model(cls, row: Dict) -> ExchangeRate:
        return ExchangeRate(
            base_currency=row.get("from_currency", ""),
            quote_currency=row.get("to_currency", ""),
            rate=float(row.get("rate", 0)),
            source=row.get("data_source"),
            update_time=row.get("updated_at"),
        )

    @classmethod
    async def save(cls, rate: ExchangeRate, rate_date: date = None) -> bool:
        """Save an exchange rate (upsert)."""
        if not cls._is_enabled():
            return False

        r_date = rate_date or date.today()

        sql = """
        INSERT INTO exchange_rates
            (from_currency, to_currency, rate, rate_date, data_source)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            rate = VALUES(rate),
            data_source = VALUES(data_source),
            updated_at = NOW()
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    sql,
                    (
                        rate.base_currency,
                        rate.quote_currency,
                        rate.rate,
                        r_date,
                        rate.source,
                    ),
                )
                return True

    @classmethod
    async def get_latest(
        cls, base_currency: str, quote_currency: str
    ) -> Optional[ExchangeRate]:
        """Get latest exchange rate for a currency pair."""
        if not cls._is_enabled():
            return None

        sql = """
        SELECT * FROM exchange_rates
        WHERE from_currency = %s AND to_currency = %s
        ORDER BY rate_date DESC
        LIMIT 1
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (base_currency, quote_currency))
                row = await cur.fetchone()
                return cls._row_to_model(row) if row else None

    @classmethod
    async def get_all_for_base(cls, base_currency: str) -> List[ExchangeRate]:
        """Get all latest rates for a base currency."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT er.* FROM exchange_rates er
        INNER JOIN (
            SELECT to_currency, MAX(rate_date) as max_date
            FROM exchange_rates
            WHERE from_currency = %s
            GROUP BY to_currency
        ) latest ON er.to_currency = latest.to_currency
                 AND er.rate_date = latest.max_date
        WHERE er.from_currency = %s
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (base_currency, base_currency))
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_history(
        cls, base_currency: str, quote_currency: str, days: int = 30
    ) -> List[ExchangeRate]:
        """Get historical rates for a currency pair."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT * FROM exchange_rates
        WHERE from_currency = %s AND to_currency = %s
        ORDER BY rate_date DESC
        LIMIT %s
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (base_currency, quote_currency, days))
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]
