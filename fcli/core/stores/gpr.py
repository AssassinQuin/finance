"""GPR (Geopolitical Risk Index) store for V2 database operations."""

from ..models import GPRHistory
from .base import BaseStore


class GPRHistoryStore(BaseStore[GPRHistory]):
    """Store for GPR history operations using V2 schema."""

    model_class = GPRHistory

    @classmethod
    def _row_to_model(cls, row: dict) -> GPRHistory:
        return GPRHistory(
            id=row.get("id"),
            country_code=row.get("country_code", "WLD"),
            report_date=row.get("report_date"),
            gpr_index=float(row.get("gpr_index", 0)),
            data_source=row.get("data_source", "Caldara-Iacoviello"),
            created_at=row.get("created_at"),
        )

    @classmethod
    async def save_batch(cls, records: list[GPRHistory]) -> int:
        """Batch save GPR history (upsert) using V2 tables."""
        if not cls._is_enabled() or not records:
            return 0

        pool = cls._pool()
        if not pool:
            return 0

        count = 0
        async with pool.acquire() as conn:
            for r in records:
                source_id = await cls._get_or_create_source(conn, r.data_source or "Caldara-Iacoviello")
                if not source_id:
                    continue

                await conn.execute(
                    """
                    INSERT INTO fact_gpr
                        (country_code, report_date, gpr_index, source_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (country_code, report_date) DO UPDATE SET
                        gpr_index = EXCLUDED.gpr_index,
                        source_id = EXCLUDED.source_id
                    """,
                    r.country_code,
                    r.report_date,
                    r.gpr_index,
                    source_id,
                )
                count += 1
            return count

    @classmethod
    async def get_latest(cls, country_code: str = "WLD") -> GPRHistory | None:
        """Get latest GPR record for a country."""
        if not cls._is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    f.id,
                    f.country_code,
                    f.report_date,
                    f.gpr_index,
                    ds.source_name as data_source,
                    f.created_at
                FROM fact_gpr f
                JOIN dim_data_source ds ON f.source_id = ds.id
                WHERE f.country_code = $1
                ORDER BY f.report_date DESC
                LIMIT 1
                """,
                country_code.upper(),
            )
            return cls._row_to_model(dict(row)) if row else None

    @classmethod
    async def get_history(cls, country_code: str = "WLD", months: int = 12) -> list[GPRHistory]:
        """Get GPR history for the last N months."""
        if not cls._is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    f.id,
                    f.country_code,
                    f.report_date,
                    f.gpr_index,
                    ds.source_name as data_source,
                    f.created_at
                FROM fact_gpr f
                JOIN dim_data_source ds ON f.source_id = ds.id
                WHERE f.country_code = $1
                ORDER BY f.report_date DESC
                LIMIT $2
                """,
                country_code.upper(),
                months,
            )
            return [cls._row_to_model(dict(row)) for row in rows]

    @classmethod
    async def _get_or_create_source(cls, conn, source_name: str) -> int | None:
        """Get or create data source in dim_data_source, return ID."""
        row = await conn.fetchrow(
            "SELECT id FROM dim_data_source WHERE source_name = $1",
            source_name,
        )

        if row:
            return row["id"]

        try:
            result = await conn.fetchrow(
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

            row = await conn.fetchrow(
                "SELECT id FROM dim_data_source WHERE source_name = $1",
                source_name,
            )
            return row["id"] if row else None
        except Exception:
            return None
