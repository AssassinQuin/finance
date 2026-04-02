"""Exchange rate store - flat table implementation."""

from datetime import datetime, timezone

from ..database import Database
from ..models import ExchangeRate
from ...utils.logger import get_logger

_logger = get_logger("fcli.stores.exchange_rate")


class ExchangeRateStore:
    """Store for exchange rate data using flat fx_rates table."""

    async def save(self, rate: ExchangeRate) -> bool:
        """Save exchange rate to fx_rates table."""
        if not Database.is_enabled():
            return False

        try:
            now = rate.update_time or datetime.now(timezone.utc)

            await Database.execute(
                """
                INSERT INTO fx_rates (
                    base_currency, quote_currency, rate_time, rate, data_source, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (base_currency, quote_currency, DATE(rate_time)) DO UPDATE SET
                    rate = EXCLUDED.rate
                """,
                rate.base_currency.upper(),
                rate.quote_currency.upper(),
                now,
                rate.rate,
                rate.source or "Frankfurter",
                now,
            )
            return True
        except Exception as e:
            _logger.error(f"Failed to save exchange rate {rate.base_currency}/{rate.quote_currency}: {e}")
            return False

    async def get_latest(self, base_currency: str, quote_currency: str) -> ExchangeRate | None:
        """Get latest exchange rate for a currency pair."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT base_currency, quote_currency, rate, rate_time, data_source
            FROM fx_rates
            WHERE base_currency = $1 AND quote_currency = $2
            ORDER BY rate_time DESC
            LIMIT 1
            """,
            base_currency.upper(),
            quote_currency.upper(),
        )

        if not row:
            return None

        return ExchangeRate(
            base_currency=row["base_currency"],
            quote_currency=row["quote_currency"],
            rate=float(row["rate"]),
            source=row["data_source"] or "Database",
            update_time=row["rate_time"],
        )

    async def get_all_for_base(self, base_currency: str) -> list[ExchangeRate]:
        """Get all latest rates for a base currency."""
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT DISTINCT ON (quote_currency)
                base_currency, quote_currency, rate, rate_time, data_source
            FROM fx_rates
            WHERE base_currency = $1
            ORDER BY quote_currency, rate_time DESC
            """,
            base_currency.upper(),
        )

        return [
            ExchangeRate(
                base_currency=row["base_currency"],
                quote_currency=row["quote_currency"],
                rate=float(row["rate"]),
                source=row["data_source"] or "Database",
                update_time=row["rate_time"],
            )
            for row in rows
        ]

    async def get_history(self, base_currency: str, quote_currency: str, days: int = 30) -> list[ExchangeRate]:
        """Get historical rates for a currency pair."""
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT base_currency, quote_currency, rate, rate_time, data_source
            FROM fx_rates
            WHERE base_currency = $1 AND quote_currency = $2
            ORDER BY rate_time DESC
            LIMIT $3
            """,
            base_currency.upper(),
            quote_currency.upper(),
            days,
        )

        return [
            ExchangeRate(
                base_currency=row["base_currency"],
                quote_currency=row["quote_currency"],
                rate=float(row["rate"]),
                source=row["data_source"] or "Database",
                update_time=row["rate_time"],
            )
            for row in rows
        ]

    def _row_to_model(self, row: dict) -> ExchangeRate:
        return ExchangeRate(
            base_currency=row.get("base_currency", ""),
            quote_currency=row.get("quote_currency", ""),
            rate=float(row.get("rate", 0)),
            source=row.get("data_source"),
            update_time=row.get("rate_time"),
        )


exchange_rate_store = ExchangeRateStore()
