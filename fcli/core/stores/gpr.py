"""GPR (Geopolitical Risk Index) store for flat table operations."""

from datetime import date, datetime

from ...utils.logger import get_logger
from ..database import Database
from ..models import GPRHistory

_logger = get_logger("fcli.stores.gpr")


class GPRHistoryStore:
    """Store for GPR history operations using flat gpr_history table."""

    def _row_to_model(self, row: dict) -> GPRHistory:
        return GPRHistory(
            id=row.get("id"),
            country_code=row.get("country_code", "WLD"),
            report_date=row["report_date"],
            gpr_index=float(row.get("gpr_index", 0)),
            index_type=row.get("index_type", "GPR"),
            data_source=row.get("data_source", "Caldara-Iacoviello"),
            created_at=row.get("created_at"),
        )

    async def ensure_schema(self) -> None:
        if not Database.is_enabled():
            return

        await Database.execute("""
            CREATE TABLE IF NOT EXISTS gpr_history (
                id SERIAL PRIMARY KEY,
                country_code VARCHAR(10) DEFAULT 'WLD',
                report_date DATE NOT NULL,
                gpr_index NUMERIC(10, 4) NOT NULL,
                index_type VARCHAR(10) DEFAULT 'GPR',
                data_source VARCHAR(50) DEFAULT 'Caldara-Iacoviello',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (country_code, report_date, index_type)
            )
        """)

        try:
            await Database.execute("""
                ALTER TABLE gpr_history ADD COLUMN IF NOT EXISTS index_type VARCHAR(10) DEFAULT 'GPR'
            """)
        except Exception:
            pass

        try:
            await Database.execute("""
                DROP INDEX IF EXISTS gpr_history_country_date_idx
            """)
            await Database.execute("""
                ALTER TABLE gpr_history DROP CONSTRAINT IF EXISTS gpr_history_country_code_report_date_key
            """)
            await Database.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS gpr_history_unique_idx
                ON gpr_history (country_code, report_date, index_type)
            """)
            await Database.execute("""
                DROP INDEX IF EXISTS gpr_history_country_code_report_date_idx
            """)
        except Exception:
            pass

    async def save_batch(self, records: list[GPRHistory]) -> int:
        if not Database.is_enabled() or not records:
            return 0

        try:
            args_list = [
                (
                    r.country_code,
                    r.report_date,
                    r.gpr_index,
                    r.index_type or "GPR",
                    r.data_source or "Caldara-Iacoviello",
                )
                for r in records
            ]
            await Database.execute_many(
                """
                INSERT INTO gpr_history (country_code, report_date, gpr_index, index_type, data_source)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (country_code, report_date, index_type) DO UPDATE SET
                    gpr_index = EXCLUDED.gpr_index
                """,
                args_list,
            )
            return len(args_list)
        except Exception as e:
            _logger.error(f"Failed to save {len(records)} GPR records: {e}")
            return 0

    async def get_latest(
        self,
        country_code: str = "WLD",
        index_type: str = "GPR",
    ) -> GPRHistory | None:
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT id, country_code, report_date, gpr_index, index_type, data_source, created_at
            FROM gpr_history
            WHERE country_code = $1 AND index_type = $2
            ORDER BY report_date DESC
            LIMIT 1
            """,
            country_code.upper(),
            index_type,
        )
        return self._row_to_model(dict(row)) if row else None

    async def get_history(
        self,
        country_code: str = "WLD",
        index_type: str = "GPR",
        months: int = 12,
    ) -> list[GPRHistory]:
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT id, country_code, report_date, gpr_index, index_type, data_source, created_at
            FROM gpr_history
            WHERE country_code = $1 AND index_type = $2
            ORDER BY report_date DESC
            LIMIT $3
            """,
            country_code.upper(),
            index_type,
            months,
        )
        return [self._row_to_model(dict(row)) for row in rows]

    async def get_latest_date(
        self,
        country_code: str = "WLD",
        index_type: str = "GPR",
    ) -> date | None:
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT MAX(report_date) as latest_date
            FROM gpr_history
            WHERE country_code = $1 AND index_type = $2
            """,
            country_code.upper(),
            index_type,
        )
        return row["latest_date"] if row else None

    async def get_last_update_time(self) -> datetime | None:
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one("SELECT MAX(created_at) as last_update FROM gpr_history")
        if row and row["last_update"]:
            return row["last_update"]
        return None

    async def get_multi_country_latest(
        self,
        country_codes: list[str],
        index_type: str = "GPR",
    ) -> list[GPRHistory]:
        if not Database.is_enabled() or not country_codes:
            return []

        codes = [c.upper() for c in country_codes]
        rows = await Database.fetch_all(
            """
            SELECT DISTINCT ON (country_code)
                id, country_code, report_date, gpr_index, index_type, data_source, created_at
            FROM gpr_history
            WHERE country_code = ANY($1) AND index_type = $2
            ORDER BY country_code, report_date DESC
            """,
            codes,
            index_type,
        )
        return [self._row_to_model(dict(row)) for row in rows]


gpr_history_store = GPRHistoryStore()
