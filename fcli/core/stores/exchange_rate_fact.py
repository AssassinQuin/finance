"""Exchange rate fact store - V2 fact table implementation."""

from datetime import datetime, timezone

from ..database import Database
from ..models import ExchangeRate
from .base import BaseStore


class ExchangeRateFactStore(BaseStore[ExchangeRate]):
    """Store for exchange rate data using V2 fact table (fact_fx_rate + dim_currency)."""

    table_name = "fact_fx_rate"

    @classmethod
    async def _get_or_create_currency_id(cls, code: str, name: str = "") -> int | None:
        """Get or create currency_id from dim_currency."""
        if not Database.is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM dim_currency WHERE currency_code = $1",
                code.upper(),
            )
            if row:
                return row["id"]

            await conn.execute(
                """
                INSERT INTO dim_currency (currency_code, currency_name)
                VALUES ($1, $2)
                """,
                code.upper(),
                name or code.upper(),
            )
            row = await conn.fetchrow(
                "SELECT id FROM dim_currency WHERE currency_code = $1",
                code.upper(),
            )
            return row["id"] if row else None

    @classmethod
    async def _get_source_id(cls, source_name: str = "Frankfurter") -> int | None:
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
    async def save(cls, rate: ExchangeRate) -> bool:
        """Save exchange rate to fact_fx_rate table."""
        if not Database.is_enabled():
            return False

        pool = cls._pool()
        if not pool:
            return False

        try:
            base_id = await cls._get_or_create_currency_id(rate.base_currency)
            quote_id = await cls._get_or_create_currency_id(rate.quote_currency)

            if not base_id or not quote_id:
                return False

            source_id = await cls._get_source_id("Frankfurter")
            now = rate.update_time or datetime.now(timezone.utc)

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO fact_fx_rate (
                        base_currency_id, quote_currency_id, rate_time, rate, source_id, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (base_currency_id, quote_currency_id, DATE(rate_time)) DO UPDATE SET
                        rate = EXCLUDED.rate,
                        source_id = EXCLUDED.source_id
                    """,
                    base_id,
                    quote_id,
                    now,
                    rate.rate,
                    source_id,
                    now,
                )
            return True
        except Exception:
            return False

    @classmethod
    async def get_latest(cls, base_currency: str, quote_currency: str) -> ExchangeRate | None:
        """Get latest exchange rate for a currency pair."""
        if not Database.is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT bc.currency_code as base, qc.currency_code as quote,
                       f.rate, f.rate_time, ds.source_name
                FROM fact_fx_rate f
                JOIN dim_currency bc ON f.base_currency_id = bc.id
                JOIN dim_currency qc ON f.quote_currency_id = qc.id
                LEFT JOIN dim_data_source ds ON f.source_id = ds.id
                WHERE bc.currency_code = $1 AND qc.currency_code = $2
                ORDER BY f.rate_time DESC
                LIMIT 1
                """,
                base_currency.upper(),
                quote_currency.upper(),
            )

        if not row:
            return None

        return ExchangeRate(
            base_currency=row["base"],
            quote_currency=row["quote"],
            rate=float(row["rate"]),
            source=row["source_name"] or "Database",
            update_time=row["rate_time"],
        )

    @classmethod
    async def get_all_for_base(cls, base_currency: str) -> list[ExchangeRate]:
        """Get all latest rates for a base currency."""
        if not Database.is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (qc.currency_code)
                    bc.currency_code as base, qc.currency_code as quote,
                    f.rate, f.rate_time, ds.source_name
                FROM fact_fx_rate f
                JOIN dim_currency bc ON f.base_currency_id = bc.id
                JOIN dim_currency qc ON f.quote_currency_id = qc.id
                LEFT JOIN dim_data_source ds ON f.source_id = ds.id
                WHERE bc.currency_code = $1
                ORDER BY qc.currency_code, f.rate_time DESC
                """,
                base_currency.upper(),
            )

        return [
            ExchangeRate(
                base_currency=row["base"],
                quote_currency=row["quote"],
                rate=float(row["rate"]),
                source=row["source_name"] or "Database",
                update_time=row["rate_time"],
            )
            for row in rows
        ]

    @classmethod
    async def get_history(cls, base_currency: str, quote_currency: str, days: int = 30) -> list[ExchangeRate]:
        """Get historical rates for a currency pair."""
        if not Database.is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT bc.currency_code as base, qc.currency_code as quote,
                       f.rate, f.rate_time, ds.source_name
                FROM fact_fx_rate f
                JOIN dim_currency bc ON f.base_currency_id = bc.id
                JOIN dim_currency qc ON f.quote_currency_id = qc.id
                LEFT JOIN dim_data_source ds ON f.source_id = ds.id
                WHERE bc.currency_code = $1 AND qc.currency_code = $2
                ORDER BY f.rate_time DESC
                LIMIT $3
                """,
                base_currency.upper(),
                quote_currency.upper(),
                days,
            )

        return [
            ExchangeRate(
                base_currency=row["base"],
                quote_currency=row["quote"],
                rate=float(row["rate"]),
                source=row["source_name"] or "Database",
                update_time=row["rate_time"],
            )
            for row in rows
        ]

    @classmethod
    def _row_to_model(cls, row: dict) -> ExchangeRate:
        return ExchangeRate(
            base_currency=row.get("base", ""),
            quote_currency=row.get("quote", ""),
            rate=float(row.get("rate", 0)),
            source=row.get("source_name"),
            update_time=row.get("rate_time"),
        )
