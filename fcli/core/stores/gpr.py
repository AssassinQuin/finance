"""GPR (Geopolitical Risk Index) store for flat table operations."""

from datetime import date

from ..database import Database
from ..models import GPRHistory


class GPRHistoryStore:
    """Store for GPR history operations using flat gpr_history table."""

    @classmethod
    def _row_to_model(cls, row: dict) -> GPRHistory:
        return GPRHistory(
            id=row.get("id"),
            country_code=row.get("country_code", "WLD"),
            report_date=row["report_date"],
            gpr_index=float(row.get("gpr_index", 0)),
            data_source=row.get("data_source", "Caldara-Iacoviello"),
            created_at=row.get("created_at"),
        )

    @classmethod
    async def save_batch(cls, records: list[GPRHistory]) -> int:
        """Batch save GPR history (upsert) using flat table."""
        if not Database.is_enabled() or not records:
            return 0

        try:
            args_list = [
                (
                    r.country_code,
                    r.report_date,
                    r.gpr_index,
                    r.data_source or "Caldara-Iacoviello",
                )
                for r in records
            ]
            await Database.execute_many(
                """
                INSERT INTO gpr_history (country_code, report_date, gpr_index, data_source)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (country_code, report_date) DO UPDATE SET
                    gpr_index = EXCLUDED.gpr_index
                """,
                args_list,
            )
            return len(args_list)
        except Exception:
            return 0

    @classmethod
    async def get_latest(cls, country_code: str = "WLD") -> GPRHistory | None:
        """Get latest GPR record for a country."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT id, country_code, report_date, gpr_index, data_source, created_at
            FROM gpr_history
            WHERE country_code = $1
            ORDER BY report_date DESC
            LIMIT 1
            """,
            country_code.upper(),
        )
        return cls._row_to_model(dict(row)) if row else None

    @classmethod
    async def get_history(cls, country_code: str = "WLD", months: int = 12) -> list[GPRHistory]:
        """Get GPR history for the last N months."""
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT id, country_code, report_date, gpr_index, data_source, created_at
            FROM gpr_history
            WHERE country_code = $1
            ORDER BY report_date DESC
            LIMIT $2
            """,
            country_code.upper(),
            months,
        )
        return [cls._row_to_model(dict(row)) for row in rows]

    @classmethod
    async def get_latest_date(cls, country_code: str = "WLD") -> date | None:
        """Get the latest data date for a country."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT MAX(report_date) as latest_date
            FROM gpr_history
            WHERE country_code = $1
            """,
            country_code.upper(),
        )
        return row["latest_date"] if row else None
