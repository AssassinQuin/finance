"""GPR (Geopolitical Risk Index) store for database operations."""

from datetime import date
from typing import List, Dict, Optional

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

        pool = cls._pool()
        if not pool:
            return 0

        async with pool.acquire() as conn:
            for r in records:
                await conn.execute(
                    """
                    INSERT INTO gpr_history
                        (country_code, report_date, gpr_index, gpr_threat, gpr_act, data_source)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (country_code, report_date) DO UPDATE SET
                        gpr_index = EXCLUDED.gpr_index,
                        gpr_threat = EXCLUDED.gpr_threat,
                        gpr_act = EXCLUDED.gpr_act,
                        data_source = EXCLUDED.data_source
                    """,
                    r.country_code,
                    r.report_date,
                    r.gpr_index,
                    r.gpr_threat,
                    r.gpr_act,
                    r.data_source,
                )
            return len(records)

    @classmethod
    async def get_latest(cls, country_code: str = "WLD") -> Optional[GPRHistory]:
        """Get latest GPR record for a country."""
        if not cls._is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM gpr_history
                WHERE country_code = $1
                ORDER BY report_date DESC
                LIMIT 1
                """,
                country_code.upper(),
            )
            return cls._row_to_model(dict(row)) if row else None

    @classmethod
    async def get_history(cls, country_code: str = "WLD", months: int = 12) -> List[GPRHistory]:
        """Get GPR history for the last N months."""
        if not cls._is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM gpr_history
                WHERE country_code = $1
                ORDER BY report_date DESC
                LIMIT $2
                """,
                country_code.upper(),
                months,
            )
            return [cls._row_to_model(dict(row)) for row in rows]
