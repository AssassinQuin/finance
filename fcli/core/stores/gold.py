"""Gold reserves store - PostgreSQL implementation."""

from datetime import date, datetime
from typing import Any, Optional

from ..database import Database
from ..models.gold import GoldReserve, CentralBankSchedule
from .base import BaseStore


class GoldReserveStore(BaseStore[GoldReserve]):
    """Store for gold reserve data using PostgreSQL."""

    table_name = "gold_reserves"

    @classmethod
    async def save(cls, data: GoldReserve) -> bool:
        """Save gold reserve data using PostgreSQL UPSERT."""
        if not Database.is_enabled():
            return False

        try:
            await Database.execute(
                f"""
                INSERT INTO {cls.table_name} (
                    country_code, country_name, gold_tonnes,
                    fetched_at, data_date
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (country_code, data_date) DO UPDATE SET
                    country_name = EXCLUDED.country_name,
                    gold_tonnes = EXCLUDED.gold_tonnes,
                    fetched_at = EXCLUDED.fetched_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                data.country_code,
                data.country_name,
                data.amount_tonnes,
                datetime.now(),
                data.report_date or date.today(),
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
        """Batch save gold reserve records using executemany."""
        if not Database.is_enabled() or not data_list:
            return 0

        pool = Database.get_pool()
        if not pool:
            return 0

        now = datetime.now()
        records = [
            (
                d.country_code,
                d.country_name,
                d.amount_tonnes,
                now,
                d.report_date or date.today(),
            )
            for d in data_list
        ]

        try:
            async with pool.acquire() as conn:
                await conn.executemany(
                    f"""
                    INSERT INTO {cls.table_name} (
                        country_code, country_name, gold_tonnes,
                        fetched_at, data_date
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (country_code, data_date) DO UPDATE SET
                        country_name = EXCLUDED.country_name,
                        gold_tonnes = EXCLUDED.gold_tonnes,
                        fetched_at = EXCLUDED.fetched_at,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    records,
                )
            return len(records)
        except Exception:
            return 0

    @classmethod
    async def get_latest(cls, country_code: Optional[str] = None) -> Optional[GoldReserve]:
        """Get latest gold reserve data."""
        if not Database.is_enabled():
            return None

        if country_code:
            row = await Database.fetch_one(
                f"""
                SELECT country_code, country_name, gold_tonnes, fetched_at, data_date
                FROM {cls.table_name}
                WHERE country_code = $1
                ORDER BY data_date DESC
                LIMIT 1
                """,
                country_code,
            )
        else:
            row = await Database.fetch_one(
                f"""
                SELECT country_code, country_name, gold_tonnes, fetched_at, data_date
                FROM {cls.table_name}
                ORDER BY data_date DESC
                LIMIT 1
                """
            )

        if not row:
            return None

        return cls._row_to_model(row)

    @classmethod
    async def get_by_date(cls, data_date: date, country_code: Optional[str] = None) -> Optional[GoldReserve]:
        """Get gold reserve data for specific date."""
        if not Database.is_enabled():
            return None

        if country_code:
            row = await Database.fetch_one(
                f"""
                SELECT country_code, country_name, gold_tonnes, fetched_at, data_date
                FROM {cls.table_name}
                WHERE country_code = $1 AND data_date = $2
                """,
                country_code,
                data_date,
            )
        else:
            row = await Database.fetch_one(
                f"""
                SELECT country_code, country_name, gold_tonnes, fetched_at, data_date
                FROM {cls.table_name}
                WHERE data_date = $1
                ORDER BY gold_tonnes DESC
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
            f"""
            SELECT country_code, country_name, gold_tonnes, fetched_at, data_date
            FROM {cls.table_name}
            WHERE data_date = $1
            ORDER BY gold_tonnes DESC
            """,
            data_date,
        )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_latest_date(cls) -> Optional[date]:
        """Get the latest data date."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(f"SELECT MAX(data_date) as max_date FROM {cls.table_name}")
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
            f"""
            SELECT country_code, MAX(data_date) as latest_date
            FROM {cls.table_name}
            GROUP BY country_code
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
            f"""
            WITH latest AS (
                SELECT DISTINCT ON (country_code)
                    country_code, country_name, gold_tonnes, data_date
                FROM {cls.table_name}
                ORDER BY country_code, data_date DESC
            ),
            changes AS (
                SELECT
                    l.country_code as code,
                    l.country_name as country,
                    l.gold_tonnes as amount,
                    l.data_date as date,
                    'IMF' as source,
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
                LEFT JOIN {cls.table_name} h1
                    ON h1.country_code = l.country_code
                    AND h1.data_date = l.data_date - INTERVAL '1 month'
                LEFT JOIN {cls.table_name} h3
                    ON h3.country_code = l.country_code
                    AND h3.data_date <= l.data_date - INTERVAL '3 months'
                    AND h3.data_date > l.data_date - INTERVAL '4 months'
                LEFT JOIN {cls.table_name} h6
                    ON h6.country_code = l.country_code
                    AND h6.data_date <= l.data_date - INTERVAL '6 months'
                    AND h6.data_date > l.data_date - INTERVAL '7 months'
                LEFT JOIN {cls.table_name} h12
                    ON h12.country_code = l.country_code
                    AND h12.data_date <= l.data_date - INTERVAL '12 months'
                    AND h12.data_date > l.data_date - INTERVAL '13 months'
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
            f"""
            SELECT country_code, country_name, gold_tonnes, fetched_at, data_date
            FROM {cls.table_name}
            WHERE country_code = $1
              AND data_date >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY data_date DESC
            """,
            country_code,
        )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    def _row_to_model(cls, row: Any) -> GoldReserve:
        return GoldReserve(
            country_code=row["country_code"],
            country_name=row["country_name"],
            amount_tonnes=float(row["gold_tonnes"]) if row["gold_tonnes"] else 0.0,
            report_date=row["data_date"],
            fetch_time=row["fetched_at"],
        )


# Alias for backward compatibility
GoldStore = GoldReserveStore


class CentralBankScheduleStore(BaseStore[CentralBankSchedule]):
    """Store for central bank schedules using PostgreSQL."""

    table_name = "central_bank_schedules"

    @classmethod
    async def save(cls, schedule: CentralBankSchedule) -> bool:
        """Save central bank schedule using PostgreSQL UPSERT."""
        if not Database.is_enabled():
            return False

        try:
            await Database.execute(
                f"""
                INSERT INTO {cls.table_name} (
                    country_code, country_name, release_frequency, release_day_of_month,
                    release_time, timezone, data_source, source_url, notes, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (country_code) DO UPDATE SET
                    country_name = EXCLUDED.country_name,
                    release_frequency = EXCLUDED.release_frequency,
                    release_day_of_month = EXCLUDED.release_day_of_month,
                    release_time = EXCLUDED.release_time,
                    timezone = EXCLUDED.timezone,
                    data_source = EXCLUDED.data_source,
                    source_url = EXCLUDED.source_url,
                    notes = EXCLUDED.notes,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
                """,
                schedule.country_code,
                schedule.country_name,
                schedule.release_frequency,
                schedule.release_day,
                None,  # release_time
                None,  # timezone
                "",  # data_source
                None,  # source_url
                None,  # notes
                schedule.is_active,
            )
            return True
        except Exception:
            return False

    @classmethod
    async def get_by_country(cls, country_code: str) -> Optional[CentralBankSchedule]:
        """Get schedule for a specific country."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            f"""
            SELECT country_code, country_name, release_frequency, release_day_of_month,
                   is_active, created_at, updated_at
            FROM {cls.table_name}
            WHERE country_code = $1
            """,
            country_code,
        )

        if not row:
            return None

        return CentralBankSchedule(
            country_code=row["country_code"],
            country_name=row["country_name"],
            release_frequency=row["release_frequency"] or "monthly",
            release_day=row["release_day_of_month"],
            is_active=row["is_active"] if row["is_active"] is not None else True,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @classmethod
    async def get_all_active(cls) -> list[CentralBankSchedule]:
        """Get all active schedules."""
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            f"""
            SELECT country_code, country_name, release_frequency, release_day_of_month,
                   is_active, created_at, updated_at
            FROM {cls.table_name}
            WHERE is_active = TRUE
            ORDER BY country_code
            """
        )

        return [
            CentralBankSchedule(
                country_code=row["country_code"],
                country_name=row["country_name"],
                release_frequency=row["release_frequency"] or "monthly",
                release_day=row["release_day_of_month"],
                is_active=True,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
