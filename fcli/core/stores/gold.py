"""Gold reserves store - PostgreSQL flat table implementation."""

from datetime import date, datetime
from typing import Any

from ..database import Database
from ..models.gold import GoldReserve


class GoldReserveStore:
    """Store for gold reserve data using flat gold_reserves table."""

    @classmethod
    async def save(cls, data: GoldReserve) -> bool:
        if not Database.is_enabled():
            return False

        try:
            await Database.execute(
                """
                INSERT INTO gold_reserves (country_code, country_name, gold_tonnes, report_date, data_source, fetched_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (country_code, report_date) DO UPDATE SET
                    gold_tonnes = EXCLUDED.gold_tonnes,
                    fetched_at = EXCLUDED.fetched_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                data.country_code,
                data.country_name,
                data.amount_tonnes,
                data.report_date or date.today(),
                data.data_source or "IMF",
                datetime.now(),
            )
            return True
        except Exception:
            return False

    @classmethod
    async def save_many(cls, data_list: list[GoldReserve]) -> int:
        return await cls.save_batch(data_list)

    @classmethod
    async def save_batch(cls, data_list: list[GoldReserve]) -> int:
        if not Database.is_enabled() or not data_list:
            return 0

        try:
            args_list = [
                (
                    d.country_code,
                    d.country_name,
                    d.amount_tonnes,
                    d.report_date or date.today(),
                    d.data_source or "IMF",
                    datetime.now(),
                )
                for d in data_list
            ]
            await Database.execute_many(
                """
                INSERT INTO gold_reserves (country_code, country_name, gold_tonnes, report_date, data_source, fetched_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (country_code, report_date) DO UPDATE SET
                    gold_tonnes = EXCLUDED.gold_tonnes,
                    fetched_at = EXCLUDED.fetched_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                args_list,
            )
            return len(args_list)
        except Exception:
            return 0

    @classmethod
    async def get_latest(cls, country_code: str | None = None) -> GoldReserve | None:
        if not Database.is_enabled():
            return None

        if country_code:
            row = await Database.fetch_one(
                """
                SELECT id, country_code, country_name, gold_tonnes,
                       report_date as data_date, fetched_at, data_source
                FROM gold_reserves
                WHERE country_code = $1
                ORDER BY report_date DESC
                LIMIT 1
                """,
                country_code,
            )
        else:
            row = await Database.fetch_one(
                """
                SELECT id, country_code, country_name, gold_tonnes,
                       report_date as data_date, fetched_at, data_source
                FROM gold_reserves
                ORDER BY report_date DESC
                LIMIT 1
                """
            )

        if not row:
            return None

        return cls._row_to_model(row)

    @classmethod
    async def get_by_date(cls, data_date: date, country_code: str | None = None) -> GoldReserve | None:
        if not Database.is_enabled():
            return None

        if country_code:
            row = await Database.fetch_one(
                """
                SELECT id, country_code, country_name, gold_tonnes,
                       report_date as data_date, fetched_at, data_source
                FROM gold_reserves
                WHERE country_code = $1 AND report_date = $2
                """,
                country_code,
                data_date,
            )
        else:
            row = await Database.fetch_one(
                """
                SELECT id, country_code, country_name, gold_tonnes,
                       report_date as data_date, fetched_at, data_source
                FROM gold_reserves
                WHERE report_date = $1
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
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT id, country_code, country_name, gold_tonnes,
                   report_date as data_date, fetched_at, data_source
            FROM gold_reserves
            WHERE report_date = $1
            ORDER BY gold_tonnes DESC
            """,
            data_date,
        )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_latest_date(cls) -> date | None:
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one("SELECT MAX(report_date) as max_date FROM gold_reserves")
        return row["max_date"] if row and row["max_date"] else None

    @classmethod
    async def get_all_latest_dates(cls) -> dict[str, date]:
        if not Database.is_enabled():
            return {}

        rows = await Database.fetch_all(
            """
            SELECT country_code, MAX(report_date) as latest_date
            FROM gold_reserves
            GROUP BY country_code
            """
        )
        return {row["country_code"]: row["latest_date"] for row in rows}

    @classmethod
    async def get_latest_with_stats(cls) -> list[dict]:
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            WITH latest AS (
                SELECT DISTINCT ON (country_code)
                    country_code, country_name,
                    gold_tonnes, report_date, data_source
                FROM gold_reserves
                ORDER BY country_code, report_date DESC
            ),
            yoy AS (
                SELECT l.*,
                    l.gold_tonnes - h_yoy.gold_tonnes as yoy_change
                FROM latest l
                LEFT JOIN LATERAL (
                    SELECT gold_tonnes FROM gold_reserves
                    WHERE country_code = l.country_code
                      AND report_date <= l.report_date - INTERVAL '1 year'
                    ORDER BY report_date DESC LIMIT 1
                ) h_yoy ON true
            ),
            ytd AS (
                SELECT y.*,
                    y.gold_tonnes - h_ytd.gold_tonnes as ytd_change
                FROM yoy y
                LEFT JOIN LATERAL (
                    SELECT gold_tonnes FROM gold_reserves
                    WHERE country_code = y.country_code
                      AND report_date >= DATE_TRUNC('year', y.report_date)
                    ORDER BY report_date ASC LIMIT 1
                ) h_ytd ON true
            ),
            trend AS (
                SELECT
                    yd.country_code, yd.country_name,
                    yd.gold_tonnes, yd.report_date, yd.data_source,
                    yd.yoy_change, yd.ytd_change,
                    REGR_SLOPE(f.gold_tonnes, EXTRACT(epoch FROM f.report_date) / 2592000.0) as monthly_trend,
                    REGR_R2(f.gold_tonnes, EXTRACT(epoch FROM f.report_date) / 2592000.0) as trend_r2,
                    COUNT(*) as data_points
                FROM ytd yd
                JOIN gold_reserves f ON f.country_code = yd.country_code
                    AND f.report_date >= yd.report_date - INTERVAL '3 years'
                    AND f.report_date <= yd.report_date
                GROUP BY yd.country_code, yd.country_name,
                         yd.gold_tonnes, yd.report_date, yd.data_source,
                         yd.yoy_change, yd.ytd_change
            )
            SELECT
                country_code, country_name, gold_tonnes, report_date,
                data_source, yoy_change, ytd_change,
                monthly_trend, trend_r2, data_points
            FROM trend
            WHERE gold_tonnes > 0
            ORDER BY gold_tonnes DESC
            """
        )
        return [dict(row) for row in rows]

    @classmethod
    async def get_country_history(
        cls,
        country_code: str,
        days: int = 365,
    ) -> list[GoldReserve]:
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT id, country_code, country_name, gold_tonnes,
                   report_date as data_date, fetched_at, data_source
            FROM gold_reserves
            WHERE country_code = $2
              AND report_date >= CURRENT_DATE - ($1 || ' days')::interval
            ORDER BY report_date DESC
            """,
            days,
            country_code,
        )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_top_countries_history(
        cls,
        top_n: int = 5,
        months: int = 36,
    ) -> dict[str, list[dict]]:
        if not Database.is_enabled():
            return {}

        latest = await Database.fetch_all(
            """
            SELECT DISTINCT ON (country_code)
                country_code, country_name, gold_tonnes
            FROM gold_reserves
            ORDER BY country_code, report_date DESC
            """
        )

        top_countries = sorted(latest, key=lambda x: x["gold_tonnes"] or 0, reverse=True)[:top_n]
        if not top_countries:
            return {}

        country_codes = [row["country_code"] for row in top_countries]
        code_to_name = {row["country_code"]: row["country_name"] for row in top_countries}

        placeholders = ", ".join(f"${i + 2}" for i in range(len(country_codes)))
        rows = await Database.fetch_all(
            f"""
            SELECT country_code, gold_tonnes, report_date
            FROM gold_reserves
            WHERE country_code IN ({placeholders})
              AND report_date >= CURRENT_DATE - ($1 || ' months')::interval
            ORDER BY country_code, report_date ASC
            """,
            str(months),
            *country_codes,
        )

        result: dict[str, list[dict]] = {}
        for row in rows:
            code = row["country_code"]
            if code not in result:
                result[code] = []
            result[code].append(
                {
                    "date": row["report_date"].strftime("%Y-%m") if row["report_date"] else "",
                    "amount": float(row["gold_tonnes"]) if row["gold_tonnes"] else 0.0,
                    "country_name": code_to_name.get(code, ""),
                }
            )

        return result

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
