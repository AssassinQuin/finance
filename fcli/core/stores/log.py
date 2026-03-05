"""Fetch log store for database operations."""

from typing import List, Dict, Optional
from datetime import datetime

from ..database import Database
from ..models import FetchLog
from .base import BaseStore


class FetchLogStore(BaseStore[FetchLog]):
    """Store for fetch logs."""

    table_name = "fetch_logs"
    model_class = FetchLog

    @classmethod
    def _row_to_model(cls, row: Dict) -> FetchLog:
        return FetchLog(
            id=row.get("id"),
            data_type=row.get("data_type", ""),
            source=row.get("source", ""),
            status=row.get("status", ""),
            records_count=row.get("records_count", 0),
            duration_ms=row.get("duration_ms", 0),
            error_message=row.get("error_message"),
            timestamp=row.get("timestamp"),
        )

    @classmethod
    async def log(cls, log_entry: FetchLog) -> bool:
        """Insert a fetch log entry."""
        if not cls._is_enabled():
            return False

        pool = cls._pool()
        if not pool:
            return False

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO fetch_logs
                    (data_type, source, status, records_count, duration_ms, error_message)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                log_entry.data_type,
                log_entry.source,
                log_entry.status,
                log_entry.records_count,
                log_entry.duration_ms,
                log_entry.error_message,
            )
            return True

    @classmethod
    async def get_recent(cls, data_type: str = "gold_reserves", limit: int = 10) -> List[FetchLog]:
        """Get recent fetch logs."""
        if not cls._is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM fetch_logs
                WHERE data_type = $1
                ORDER BY timestamp DESC
                LIMIT $2
                """,
                data_type,
                limit,
            )
            return [cls._row_to_model(dict(row)) for row in rows]

    @classmethod
    async def create_log(
        cls,
        data_type: str,
        source: str,
        status: str,
        records_count: int = 0,
        duration_ms: int = 0,
        error_message: Optional[str] = None,
    ) -> bool:
        """Convenience method to create a log entry."""
        log_entry = FetchLog(
            data_type=data_type,
            source=source,
            status=status,
            records_count=records_count,
            duration_ms=duration_ms,
            error_message=error_message,
            timestamp=datetime.now(),
        )
        return await cls.log(log_entry)
