"""GPR (Geopolitical Risk Index) store for database operations."""

from datetime import date
from typing import List, Dict, Optional
import aiomysql

from ..database import Database
from ..models import GPRHistory
from .base import BaseStore


class GPRHistoryStore(BaseStore[GPRHistory]):
    """Store for GPR history operations."""

    table_name = "gpr_history"
    model_class = GPRHistory

    @classmethod
    def _row_to_model(cls, row: Dict) -> GPRHistory:
        return GPRHistory(
            id=row.get("id"),
            country_code=row.get("country_code", "WLD"),
            report_date=row.get("report_date"),
            gpr_index=float(row.get("gpr_index", 0)),
            gpr_threat=float(row["gpr_threat"]) if row.get("gpr_threat") else None,
            gpr_act=float(row["gpr_act"]) if row.get("gpr_act") else None,
            data_source=row.get("data_source", "Caldara-Iacoviello"),
            created_at=row.get("created_at"),
        )

    @classmethod
    async def save_batch(cls, records: List[GPRHistory]) -> int:
        """Batch save GPR history (upsert)."""
        if not cls._is_enabled() or not records:
            return 0

        sql = """
        INSERT INTO gpr_history
            (country_code, report_date, gpr_index, gpr_threat, gpr_act, data_source)
        VALUES (%s, %s, %s, %s, %s, %s) AS new
        ON DUPLICATE KEY UPDATE
            gpr_index = new.gpr_index,
            gpr_threat = new.gpr_threat,
            gpr_act = new.gpr_act,
            data_source = new.data_source
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                values = [
                    (
                        r.country_code,
                        r.report_date,
                        r.gpr_index,
                        r.gpr_threat,
                        r.gpr_act,
                        r.data_source,
                    )
                    for r in records
                ]
                await cur.executemany(sql, values)
                return len(values)

    @classmethod
    async def get_latest(cls, country_code: str = "WLD") -> Optional[GPRHistory]:
        """Get latest GPR record for a country."""
        if not cls._is_enabled():
            return None

        sql = """
        SELECT * FROM gpr_history
        WHERE country_code = %s
        ORDER BY report_date DESC
        LIMIT 1
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (country_code.upper(),))
                row = await cur.fetchone()
                return cls._row_to_model(row) if row else None

    @classmethod
    async def get_history(cls, country_code: str = "WLD", months: int = 12) -> List[GPRHistory]:
        """Get GPR history for the last N months."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT * FROM gpr_history
        WHERE country_code = %s
        ORDER BY report_date DESC
        LIMIT %s
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (country_code.upper(), months))
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]
