"""Exchange rate store for database operations."""

from typing import List, Dict, Optional
from datetime import date

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

        pool = cls._pool()
        if not pool:
            return False

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO exchange_rates
                    (from_currency, to_currency, rate, rate_date, data_source)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (from_currency, to_currency, rate_date) DO UPDATE SET
                    rate = EXCLUDED.rate,
                    data_source = EXCLUDED.data_source,
                    updated_at = CURRENT_TIMESTAMP
                """,
                rate.base_currency,
                rate.quote_currency,
                rate.rate,
                r_date,
                rate.source,
            )
            return True

    @classmethod
    async def get_latest(cls, base_currency: str, quote_currency: str) -> Optional[ExchangeRate]:
        """Get latest exchange rate for a currency pair."""
        if not cls._is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM exchange_rates
                WHERE from_currency = $1 AND to_currency = $2
                ORDER BY rate_date DESC
                LIMIT 1
                """,
                base_currency,
                quote_currency,
            )
            return cls._row_to_model(dict(row)) if row else None

    @classmethod
    async def get_all_for_base(cls, base_currency: str) -> List[ExchangeRate]:
        """Get all latest rates for a base currency."""
        if not cls._is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT er.* FROM exchange_rates er
                INNER JOIN (
                    SELECT to_currency, MAX(rate_date) as max_date
                    FROM exchange_rates
                    WHERE from_currency = $1
                    GROUP BY to_currency
                ) latest ON er.to_currency = latest.to_currency
                         AND er.rate_date = latest.max_date
                WHERE er.from_currency = $1
                """,
                base_currency,
            )
            return [cls._row_to_model(dict(row)) for row in rows]

    @classmethod
    async def get_history(cls, base_currency: str, quote_currency: str, days: int = 30) -> List[ExchangeRate]:
        """Get historical rates for a currency pair."""
        if not cls._is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM exchange_rates
                WHERE from_currency = $1 AND to_currency = $2
                ORDER BY rate_date DESC
                LIMIT $3
                """,
                base_currency,
                quote_currency,
                days,
            )
            return [cls._row_to_model(dict(row)) for row in rows]
