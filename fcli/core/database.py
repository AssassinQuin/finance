import asyncio
import logging
from typing import Optional

import aiomysql

from .config import config
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class Database:
    """Database connection pool manager - handles MySQL connections."""

    _pool: Optional[aiomysql.Pool] = None
    _enabled: bool = False

    @classmethod
    async def init(cls, config_obj=None) -> bool:
        """Initialize database connection pool."""
        if cls._pool is not None:
            return True

        cfg = config_obj or config

        try:
            cls._pool = await aiomysql.create_pool(
                host=cfg.db.host,
                port=cfg.db.port,
                user=cfg.db.user,
                password=cfg.db.password,
                db=cfg.db.database,
                minsize=cfg.db.pool_min,
                maxsize=cfg.db.pool_max,
                charset="utf8mb4",
                autocommit=True,
            )
            cls._enabled = True

            async with cls._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")

            return True
        except Exception as e:
            cls._enabled = False
            logger.error(f"Database initialization failed: {e}")
            return False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if database is enabled and available."""
        return cls._enabled and cls._pool is not None

    @classmethod
    def get_pool(cls) -> Optional[aiomysql.Pool]:
        """Get connection pool."""
        return cls._pool

    @classmethod
    async def close(cls):
        """Close all connections."""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            cls._enabled = False

    @classmethod
    async def execute(cls, sql: str, params: tuple = None):
        """Execute a single SQL statement."""
        if not cls.is_enabled():
            raise DatabaseError("Database not enabled")

        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return cur.rowcount

    @classmethod
    async def fetch_one(cls, sql: str, params: tuple = None):
        """Fetch a single row."""
        if not cls.is_enabled():
            return None

        async with cls._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, params)
                return await cur.fetchone()

    @classmethod
    async def fetch_all(cls, sql: str, params: tuple = None):
        """Fetch all rows."""
        if not cls.is_enabled():
            return []

        async with cls._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()
