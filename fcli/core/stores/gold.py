"""Gold reserve store for database operations."""

from datetime import date
from typing import List, Dict, Any, Optional
import aiomysql

from ..database import Database
from ..models import GoldReserve, CentralBankSchedule
from .base import BaseStore


class GoldReserveStore(BaseStore[GoldReserve]):
    """Store for gold reserve operations."""

    table_name = "gold_reserves"
    model_class = GoldReserve

    @classmethod
    def _row_to_model(cls, row: Dict) -> GoldReserve:
        return GoldReserve(
            id=row.get("id"),
            country_code=row.get("country_code", ""),
            country_name=row.get("country_name", ""),
            amount_tonnes=float(row.get("amount_tonnes", 0)),
            gold_share_pct=float(row["gold_share_pct"]) if row.get("gold_share_pct") else None,
            gold_value_usd_m=float(row["gold_value_usd_m"]) if row.get("gold_value_usd_m") else None,
            percent_of_reserves=float(row["percent_of_reserves"]) if row.get("percent_of_reserves") else None,
            report_date=row.get("report_date"),
            data_source=row.get("data_source", ""),
            fetch_time=row.get("fetch_time"),
        )

    @classmethod
    async def save_batch(cls, reserves: List[GoldReserve]) -> int:
        """Batch save gold reserves (upsert)."""
        if not cls._is_enabled() or not reserves:
            return 0

        sql = """
        INSERT INTO gold_reserves
            (country_code, country_name, amount_tonnes, gold_share_pct, gold_value_usd_m,
             percent_of_reserves, report_date, data_source, fetch_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            country_name = VALUES(country_name),
            amount_tonnes = VALUES(amount_tonnes),
            gold_share_pct = VALUES(gold_share_pct),
            gold_value_usd_m = VALUES(gold_value_usd_m),
            percent_of_reserves = VALUES(percent_of_reserves),
            data_source = VALUES(data_source),
            fetch_time = VALUES(fetch_time)
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                values = [
                    (
                        r.country_code,
                        r.country_name,
                        r.amount_tonnes,
                        r.gold_share_pct,
                        r.gold_value_usd_m,
                        r.percent_of_reserves,
                        r.report_date,
                        r.data_source,
                        r.fetch_time,
                    )
                    for r in reserves
                ]
                await cur.executemany(sql, values)
                return len(values)

    @classmethod
    async def get_latest(cls, limit: int = 20) -> List[GoldReserve]:
        """Get latest gold reserves for all countries."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT gr.*
        FROM gold_reserves gr
        INNER JOIN (
            SELECT country_code, MAX(report_date) as max_date
            FROM gold_reserves
            GROUP BY country_code
        ) latest ON gr.country_code = latest.country_code
                 AND gr.report_date = latest.max_date
        ORDER BY gr.amount_tonnes DESC
        LIMIT %s
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (limit,))
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_history(cls, country_code: str, months: int = 24) -> List[GoldReserve]:
        """Get historical gold reserves for a country."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT * FROM gold_reserves
        WHERE country_code = %s
        ORDER BY report_date DESC
        LIMIT %s
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (country_code.upper(), months))
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_latest_with_changes(cls) -> List[Dict[str, Any]]:
        """Get latest reserves with month-over-month and year-over-year changes."""
        if not cls._is_enabled():
            return []

        sql = """
        WITH latest AS (
            SELECT country_code, country_name, amount_tonnes, percent_of_reserves,
                   report_date, data_source
            FROM gold_reserves gr1
            WHERE report_date = (
                SELECT MAX(report_date) FROM gold_reserves gr2
                WHERE gr2.country_code = gr1.country_code
            )
        ),
        prev_1m AS (
            SELECT country_code, amount_tonnes as prev_1m_amount
            FROM gold_reserves gr
            WHERE report_date = (
                SELECT DISTINCT report_date FROM gold_reserves
                ORDER BY report_date DESC LIMIT 1 OFFSET 1
            )
        ),
        prev_1y AS (
            SELECT country_code, amount_tonnes as prev_1y_amount
            FROM gold_reserves gr
            WHERE report_date = (
                SELECT DATE_SUB(MAX(report_date), INTERVAL 1 YEAR) FROM gold_reserves
            )
        )
        SELECT
            l.country_code as code,
            l.country_name as country,
            l.amount_tonnes as amount,
            l.percent_of_reserves,
            DATE_FORMAT(l.report_date, '%Y-%m') as date,
            l.data_source as source,
            COALESCE(l.amount_tonnes - p1.prev_1m_amount, 0) as change_1m,
            COALESCE(l.amount_tonnes - p2.prev_1y_amount, 0) as change_1y
        FROM latest l
        LEFT JOIN prev_1m p1 ON l.country_code = p1.country_code
        LEFT JOIN prev_1y p2 ON l.country_code = p2.country_code
        ORDER BY l.amount_tonnes DESC
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return [dict(row) for row in rows]

    @classmethod
    async def get_latest_with_multi_period_changes(cls) -> List[Dict[str, Any]]:
        """Get latest reserves with 1m, 3m, 6m, 12m changes."""
        if not cls._is_enabled():
            return []

        sql = """
        WITH latest AS (
            SELECT gr.country_code, gr.country_name, gr.amount_tonnes, gr.percent_of_reserves,
                   gr.report_date, gr.data_source
            FROM gold_reserves gr
            INNER JOIN (
                SELECT country_code, MAX(report_date) as max_date FROM gold_reserves GROUP BY country_code
            ) m ON gr.country_code = m.country_code AND gr.report_date = m.max_date
        )
        SELECT
            l.country_code as code,
            l.country_name as country,
            l.amount_tonnes as amount,
            l.percent_of_reserves,
            DATE_FORMAT(l.report_date, '%Y-%m') as date,
            l.data_source as source,
            COALESCE(l.amount_tonnes - (
                SELECT g.amount_tonnes FROM gold_reserves g
                WHERE g.country_code = l.country_code AND g.report_date < l.report_date
                ORDER BY g.report_date DESC LIMIT 1
            ), 0) as change_1m,
            COALESCE(l.amount_tonnes - (
                SELECT g.amount_tonnes FROM gold_reserves g
                WHERE g.country_code = l.country_code AND g.report_date < l.report_date
                ORDER BY g.report_date DESC LIMIT 1 OFFSET 2
            ), 0) as change_3m,
            COALESCE(l.amount_tonnes - (
                SELECT g.amount_tonnes FROM gold_reserves g
                WHERE g.country_code = l.country_code AND g.report_date < l.report_date
                ORDER BY g.report_date DESC LIMIT 1 OFFSET 5
            ), 0) as change_6m,
            COALESCE(l.amount_tonnes - (
                SELECT g.amount_tonnes FROM gold_reserves g
                WHERE g.country_code = l.country_code AND g.report_date < l.report_date
                ORDER BY g.report_date DESC LIMIT 1 OFFSET 11
            ), 0) as change_12m
        FROM latest l
        ORDER BY l.amount_tonnes DESC
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return [dict(row) for row in rows]

    @classmethod
    async def get_all_latest_dates(cls) -> Dict[str, date]:
        """Get the latest report date for each country."""
        if not cls._is_enabled():
            return {}

        sql = """
        SELECT country_code, MAX(report_date) as latest_date
        FROM gold_reserves
        GROUP BY country_code
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return {row["country_code"]: row["latest_date"] for row in rows}




class CentralBankScheduleStore(BaseStore[CentralBankSchedule]):
    """Store for central bank schedules."""

    table_name = "central_bank_schedules"
    model_class = CentralBankSchedule

    @classmethod
    def _row_to_model(cls, row: Dict) -> CentralBankSchedule:
        return CentralBankSchedule(
            id=row.get("id"),
            country_code=row.get("country_code", ""),
            country_name=row.get("country_name", ""),
            release_day=row.get("release_day"),
            release_frequency=row.get("release_frequency", "monthly"),
            last_release_date=row.get("last_release_date"),
            next_expected_date=row.get("next_expected_date"),
            is_active=bool(row.get("is_active", True)),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @classmethod
    async def get_all_active(cls) -> List[CentralBankSchedule]:
        """Get all active central bank schedules."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT * FROM central_bank_schedules
        WHERE is_active = TRUE
        ORDER BY country_code
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def get_by_country(cls, country_code: str) -> Optional[CentralBankSchedule]:
        """Get schedule for a specific country."""
        if not cls._is_enabled():
            return None

        sql = "SELECT * FROM central_bank_schedules WHERE country_code = %s"

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (country_code.upper(),))
                row = await cur.fetchone()
                return cls._row_to_model(row) if row else None

    @classmethod
    async def update_schedule(cls, schedule: CentralBankSchedule) -> bool:
        """Insert or update a schedule."""
        if not cls._is_enabled():
            return False

        sql = """
        INSERT INTO central_bank_schedules
            (country_code, country_name, release_day, release_frequency,
             last_release_date, next_expected_date, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            country_name = VALUES(country_name),
            release_day = VALUES(release_day),
            release_frequency = VALUES(release_frequency),
            last_release_date = VALUES(last_release_date),
            next_expected_date = VALUES(next_expected_date),
            is_active = VALUES(is_active),
            updated_at = NOW()
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    sql,
                    (
                        schedule.country_code,
                        schedule.country_name,
                        schedule.release_day,
                        schedule.release_frequency,
                        schedule.last_release_date,
                        schedule.next_expected_date,
                        schedule.is_active,
                    ),
                )
                return True

    @classmethod
    async def init_default_schedules(cls):
        """Initialize default schedules for top 20 countries."""
        default_schedules = [
            {"code": "USA", "name": "美国", "release_day": 28, "frequency": "monthly"},
            {"code": "DEU", "name": "德国", "release_day": 6, "frequency": "monthly"},
            {"code": "ITA", "name": "意大利", "release_day": 7, "frequency": "monthly"},
            {"code": "FRA", "name": "法国", "release_day": 24, "frequency": "monthly"},
            {"code": "RUS", "name": "俄罗斯", "release_day": 10, "frequency": "monthly"},
            {"code": "CHN", "name": "中国", "release_day": 7, "frequency": "monthly"},
            {"code": "CHE", "name": "瑞士", "release_day": 23, "frequency": "monthly"},
            {"code": "JPN", "name": "日本", "release_day": 22, "frequency": "monthly"},
            {"code": "IND", "name": "印度", "release_day": 5, "frequency": "weekly"},
            {"code": "NLD", "name": "荷兰", "release_day": 10, "frequency": "monthly"},
            {"code": "TUR", "name": "土耳其", "release_day": 15, "frequency": "monthly"},
            {"code": "PRT", "name": "葡萄牙", "release_day": 10, "frequency": "monthly"},
            {"code": "UZB", "name": "乌兹别克斯坦", "release_day": 15, "frequency": "monthly"},
            {"code": "SAU", "name": "沙特阿拉伯", "release_day": 20, "frequency": "monthly"},
            {"code": "GBR", "name": "英国", "release_day": 20, "frequency": "monthly"},
            {"code": "KAZ", "name": "哈萨克斯坦", "release_day": 10, "frequency": "monthly"},
            {"code": "ESP", "name": "西班牙", "release_day": 15, "frequency": "monthly"},
            {"code": "AUT", "name": "奥地利", "release_day": 10, "frequency": "monthly"},
            {"code": "THA", "name": "泰国", "release_day": 10, "frequency": "monthly"},
            {"code": "SGP", "name": "新加坡", "release_day": 25, "frequency": "monthly"},
        ]

        for sched in default_schedules:
            schedule = CentralBankSchedule(
                country_code=sched["code"],
                country_name=sched["name"],
                release_day=sched["release_day"],
                release_frequency=sched["frequency"],
                is_active=True,
            )
            await cls.update_schedule(schedule)
