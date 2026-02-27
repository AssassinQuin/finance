"""Fetch log store for database operations."""

from typing import List, Dict, Optional
from datetime import datetime
import aiomysql

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

        sql = """
        INSERT INTO fetch_logs
            (data_type, source, status, records_count, duration_ms, error_message)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    sql,
                    (
                        log_entry.data_type,
                        log_entry.source,
                        log_entry.status,
                        log_entry.records_count,
                        log_entry.duration_ms,
                        log_entry.error_message,
                    ),
                )
                return True

    @classmethod
    async def get_recent(cls, data_type: str = "gold_reserves", limit: int = 10) -> List[FetchLog]:
        """Get recent fetch logs."""
        if not cls._is_enabled():
            return []

        sql = """
        SELECT * FROM fetch_logs
        WHERE data_type = %s
        ORDER BY timestamp DESC
        LIMIT %s
        """

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (data_type, limit))
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]

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
