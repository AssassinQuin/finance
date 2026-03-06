"""PostgreSQL database connection pool manager.

Replaces MySQL (aiomysql) with PostgreSQL (asyncpg) for "Just Use Postgres" architecture.
"""

import logging

import asyncpg

from .config import config
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL connection pool manager."""

    _pool: asyncpg.Pool | None = None
    _enabled: bool = False

    @classmethod
    async def init(cls, config_obj=None) -> bool:
        """Initialize PostgreSQL connection pool."""
        if cls._pool is not None:
            return True

        cfg = config_obj or config

        try:
            cls._pool = await asyncpg.create_pool(
                host=cfg.db.host,
                port=cfg.db.port,
                user=cfg.db.user,
                password=cfg.db.password,
                database=cfg.db.database,
                min_size=cfg.db.pool_min,
                max_size=cfg.db.pool_max,
                command_timeout=60,
            )
            cls._enabled = True

            # Test connection
            async with cls._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            logger.info(f"PostgreSQL connected: {cfg.db.host}:{cfg.db.port}/{cfg.db.database}")
            return True
        except Exception as e:
            cls._enabled = False
            logger.error(f"PostgreSQL initialization failed: {e}")
            return False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if database is enabled and available."""
        return cls._enabled and cls._pool is not None

    @classmethod
    def get_pool(cls) -> asyncpg.Pool | None:
        """Get connection pool."""
        return cls._pool

    @classmethod
    async def close(cls):
        """Close all connections."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            cls._enabled = False
            logger.info("PostgreSQL connection pool closed")

    @classmethod
    async def execute(cls, sql: str, *args) -> int:
        """Execute a single SQL statement.

        Returns:
            Number of rows affected
        """
        if not cls.is_enabled():
            raise DatabaseError("Database not enabled")

        async with cls._pool.acquire() as conn:
            return await conn.execute(sql, *args)

    @classmethod
    async def fetch_one(cls, sql: str, *args) -> asyncpg.Record | None:
        """Fetch a single row."""
        if not cls.is_enabled():
            return None

        async with cls._pool.acquire() as conn:
            return await conn.fetchrow(sql, *args)

    @classmethod
    async def fetch_all(cls, sql: str, *args) -> list[asyncpg.Record]:
        """Fetch all rows."""
        if not cls.is_enabled():
            return []

        async with cls._pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    @classmethod
    async def fetchval(cls, sql: str, *args):
        """Fetch a single value."""
        if not cls.is_enabled():
            return None

        async with cls._pool.acquire() as conn:
            return await conn.fetchval(sql, *args)

    @classmethod
    async def execute_many(cls, sql: str, args_list: list) -> int:
        """Execute SQL with multiple parameter sets (batch insert/update)."""
        if not cls.is_enabled():
            raise DatabaseError("Database not enabled")

        async with cls._pool.acquire() as conn:
            result = await conn.executemany(sql, args_list)
            # asyncpg returns 'INSERT 0 3' style string, extract count
            if isinstance(result, str):
                parts = result.split()
                return int(parts[-1]) if parts else 0
            return 0

    @classmethod
    async def transaction(cls):
        """Get a transaction context manager."""
        if not cls.is_enabled():
            raise DatabaseError("Database not enabled")

        return cls._pool.acquire()

    @classmethod
    def row_to_dict(cls, row: asyncpg.Record | None) -> dict | None:
        """Convert asyncpg Record to dict."""
        if row is None:
            return None
        return dict(row)
