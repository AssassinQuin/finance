"""Gold reserves store - PostgreSQL implementation with V2 schema."""

from datetime import date, datetime
from typing import Any

from ..database import Database
from ..models.gold import GoldReserve
from .base import BaseStore


class GoldReserveStore(BaseStore[GoldReserve]):
    """Store for gold reserve data using PostgreSQL V2 schema."""

    @classmethod
    async def save(cls, data: GoldReserve) -> bool:
        """Save gold reserve data using PostgreSQL UPSERT with V2 tables."""
        if not Database.is_enabled():
            return False

        try:
            country_id = await cls._get_or_create_country(data.country_code, data.country_name)
            source_id = await cls._get_or_create_source(data.data_source or "IMF")

            if not country_id or not source_id:
                return False

            await Database.execute(
                """
                INSERT INTO fact_gold_reserve (
                    country_id, report_date, gold_tonnes,
                    fetched_at, source_id
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (country_id, report_date) DO UPDATE SET
                    gold_tonnes = EXCLUDED.gold_tonnes,
                    fetched_at = EXCLUDED.fetched_at,
                    source_id = EXCLUDED.source_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                country_id,
                data.report_date or date.today(),
                data.amount_tonnes,
                datetime.now(),
                source_id,
            )
            return True
        except Exception:
            return False

    @classmethod
    async def save_many(cls, data_list: list[GoldReserve]) -> int:
        """Save multiple gold reserve records."""
        if not Database.is_enabled():
            return 0

        count = 0
        for data in data_list:
            if await cls.save(data):
                count += 1
        return count

    @classmethod
    async def save_batch(cls, data_list: list[GoldReserve]) -> int:
        """Batch save gold reserve records."""
        if not Database.is_enabled() or not data_list:
            return 0

        count = 0
        for data in data_list:
            if await cls.save(data):
                count += 1
        return count

    @classmethod
    async def get_latest(cls, country_code: str | None = None) -> GoldReserve | None:
        """Get latest gold reserve data."""
        if not Database.is_enabled():
            return None

        if country_code:
            row = await Database.fetch_one(
                """
                SELECT 
                    f.id,
                    c.country_code,
                    c.country_name,
                    f.gold_tonnes,
                    f.report_date as data_date,
                    f.fetched_at,
                    ds.source_name as data_source
                FROM fact_gold_reserve f
                JOIN dim_country c ON f.country_id = c.id
                JOIN dim_data_source ds ON f.source_id = ds.id
                WHERE c.country_code = $1
                ORDER BY f.report_date DESC
                LIMIT 1
                """,
                country_code,
            )
        else:
            row = await Database.fetch_one(
                """
                SELECT 
                    f.id,
                    c.country_code,
                    c.country_name,
                    f.gold_tonnes,
                    f.report_date as data_date,
                    f.fetched_at,
                    ds.source_name as data_source
                FROM fact_gold_reserve f
                JOIN dim_country c ON f.country_id = c.id
                JOIN dim_data_source ds ON f.source_id = ds.id
                ORDER BY f.report_date DESC
                LIMIT 1
                """
            )

        if not row:
            return None

        return cls._row_to_model(row)

    @classmethod
    async def get_by_date(cls, data_date: date, country_code: str | None = None) -> GoldReserve | None:
        """Get gold reserve data for specific date."""
        if not Database.is_enabled():
            return None

        if country_code:
            row = await Database.fetch_one(
                """
                SELECT 
                    f.id,
                    c.country_code,
                    c.country_name,
                    f.gold_tonnes,
                    f.report_date as data_date,
                    f.fetched_at,
                    ds.source_name as data_source
                FROM fact_gold_reserve f
                JOIN dim_country c ON f.country_id = c.id
                JOIN dim_data_source ds ON f.source_id = ds.id
                WHERE c.country_code = $1 AND f.report_date = $2
                """,
                country_code,
                data_date,
            )
        else:
            row = await Database.fetch_one(
                """
                SELECT 
                    f.id,
                    c.country_code,
                    c.country_name,
                    f.gold_tonnes,
                    f.report_date as data_date,
                    f.fetched_at,
                    ds.source_name as data_source
                FROM fact_gold_reserve f
                JOIN dim_country c ON f.country_id = c.id
                JOIN dim_data_source ds ON f.source_id = ds.id
                WHERE f.report_date = $1
                ORDER BY f.gold_tonnes DESC
                LIMIT 1
                """,
                data_date,
            )

        if not row:
            return None

        return cls._row_to_model(row)

    @classmethod
    async def get_all_by_date(cls, data_date: date) -> list[GoldReserve]:
        """Get all countries' data for a specific date."""
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT 
                f.id,
                c.country_code,
                c.country_name,
                f.gold_tonnes,
                f.report_date as data_date,
                f.fetched_at,
                ds.source_name as data_source
            FROM fact_gold_reserve f
            JOIN dim_country c ON f.country_id = c.id
            JOIN dim_data_source ds ON f.source_id = ds.id
            WHERE f.report_date = $1
            ORDER BY f.gold_tonnes DESC
            """,
            data_date,
        )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_latest_date(cls) -> date | None:
        """Get the latest data date."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one("SELECT MAX(report_date) as max_date FROM fact_gold_reserve")
        return row["max_date"] if row and row["max_date"] else None

    @classmethod
    async def get_all_latest_dates(cls) -> dict[str, date]:
        """Get the latest data date for each country.

        Returns:
            Dict mapping country_code -> latest data_date
        """
        if not Database.is_enabled():
            return {}

        rows = await Database.fetch_all(
            """
            SELECT c.country_code, MAX(f.report_date) as latest_date
            FROM fact_gold_reserve f
            JOIN dim_country c ON f.country_id = c.id
            GROUP BY c.country_code
            """
        )
        return {row["country_code"]: row["latest_date"] for row in rows}

    @classmethod
    async def get_latest_with_multi_period_changes(cls) -> list[dict]:
        """Get latest reserves with 1/3/6/12 month changes.

        Returns:
            List of dicts with country, code, amount, date, source,
            and change_1m, change_3m, change_6m, change_12m
        """
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            WITH latest AS (
                SELECT DISTINCT ON (f.country_id)
                    f.country_id,
                    c.country_code,
                    c.country_name,
                    f.gold_tonnes,
                    f.report_date,
                    ds.source_name
                FROM fact_gold_reserve f
                JOIN dim_country c ON f.country_id = c.id
                JOIN dim_data_source ds ON f.source_id = ds.id
                ORDER BY f.country_id, f.report_date DESC
            ),
            changes AS (
                SELECT
                    l.country_code as code,
                    l.country_name as country,
                    l.gold_tonnes as amount,
                    l.report_date as date,
                    l.source_name as source,
                    COALESCE(
                        (l.gold_tonnes - h1.gold_tonnes) / NULLIF(h1.gold_tonnes, 0) * 100,
                        0
                    ) as change_1m,
                    COALESCE(
                        (l.gold_tonnes - h3.gold_tonnes) / NULLIF(h3.gold_tonnes, 0) * 100,
                        0
                    ) as change_3m,
                    COALESCE(
                        (l.gold_tonnes - h6.gold_tonnes) / NULLIF(h6.gold_tonnes, 0) * 100,
                        0
                    ) as change_6m,
                    COALESCE(
                        (l.gold_tonnes - h12.gold_tonnes) / NULLIF(h12.gold_tonnes, 0) * 100,
                        0
                    ) as change_12m
                FROM latest l
                LEFT JOIN fact_gold_reserve h1
                    ON h1.country_id = l.country_id
                    AND h1.report_date = l.report_date - INTERVAL '1 month'
                LEFT JOIN fact_gold_reserve h3
                    ON h3.country_id = l.country_id
                    AND h3.report_date <= l.report_date - INTERVAL '3 months'
                    AND h3.report_date > l.report_date - INTERVAL '4 months'
                LEFT JOIN fact_gold_reserve h6
                    ON h6.country_id = l.country_id
                    AND h6.report_date <= l.report_date - INTERVAL '6 months'
                    AND h6.report_date > l.report_date - INTERVAL '7 months'
                LEFT JOIN fact_gold_reserve h12
                    ON h12.country_id = l.country_id
                    AND h12.report_date <= l.report_date - INTERVAL '12 months'
                    AND h12.report_date > l.report_date - INTERVAL '13 months'
            )
            SELECT * FROM changes
            WHERE amount > 0
            ORDER BY amount DESC
            """
        )
        return [dict(row) for row in rows]

    @classmethod
    async def get_country_history(
        cls,
        country_code: str,
        days: int = 365,
    ) -> list[GoldReserve]:
        """Get historical data for a country."""
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT 
                f.id,
                c.country_code,
                c.country_name,
                f.gold_tonnes,
                f.report_date as data_date,
                f.fetched_at,
                ds.source_name as data_source
            FROM fact_gold_reserve f
            JOIN dim_country c ON f.country_id = c.id
            JOIN dim_data_source ds ON f.source_id = ds.id
            WHERE c.country_code = $1
              AND f.report_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY f.report_date DESC
            """
            % days,
            country_code,
        )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def _get_or_create_country(cls, country_code: str, country_name: str) -> int | None:
        """Get or create country in dim_country, return ID."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            "SELECT id FROM dim_country WHERE country_code = $1",
            country_code,
        )

        if row:
            return row["id"]

        try:
            result = await Database.fetch_one(
                """
                INSERT INTO dim_country (country_code, country_name)
                VALUES ($1, $2)
                ON CONFLICT (country_code) DO UPDATE SET country_name = EXCLUDED.country_name
                RETURNING id
                """,
                country_code,
                country_name,
            )
            return result["id"] if result else None
        except Exception:
            return None

    @classmethod
    async def _get_or_create_source(cls, source_name: str) -> int | None:
        """Get or create data source in dim_data_source, return ID."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            "SELECT id FROM dim_data_source WHERE source_name = $1",
            source_name,
        )

        if row:
            return row["id"]

        try:
            result = await Database.fetch_one(
                """
                INSERT INTO dim_data_source (source_name)
                VALUES ($1)
                ON CONFLICT (source_name) DO NOTHING
                RETURNING id
                """,
                source_name,
            )
            if result:
                return result["id"]

            row = await Database.fetch_one(
                "SELECT id FROM dim_data_source WHERE source_name = $1",
                source_name,
            )
            return row["id"] if row else None
        except Exception:
            return None

    @classmethod
    def _row_to_model(cls, row: Any) -> GoldReserve:
        return GoldReserve(
            country_code=row["country_code"],
            country_name=row["country_name"],
            amount_tonnes=float(row["gold_tonnes"]) if row["gold_tonnes"] else 0.0,
            report_date=row["data_date"],
            fetch_time=row["fetched_at"],
            data_source=row.get("data_source", ""),
        )


GoldStore = GoldReserveStore
