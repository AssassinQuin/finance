"""PostgreSQL database connection pool manager.

Replaces MySQL (aiomysql) with PostgreSQL (asyncpg) for "Just Use Postgres" architecture.

Usage:
    # No manual init/close needed - auto-initialized on first use
    rows = await Database.fetch_all("SELECT * FROM table")

    # Auto-cleanup on application exit (registered via atexit)
"""

import asyncio
import atexit
from contextlib import asynccontextmanager
from typing import AsyncContextManager

import asyncpg

from .config import config
from .exceptions import DatabaseError
from ..utils.logger import get_logger


class _TransactionContext:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._conn: asyncpg.Connection | None = None
        self._tx: "asyncpg.Transaction | None" = None

    async def __aenter__(self) -> "asyncpg.Transaction":
        self._conn = await self._pool.acquire()
        self._tx = self._conn.transaction()
        await self._tx.__aenter__()
        return self._tx

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._tx:
            await self._tx.__aexit__(exc_type, exc_val, exc_tb)
        if self._conn:
            await self._conn.close()


logger = get_logger("fcli.database")


class Database:
    """PostgreSQL connection pool manager with auto-lazy-initialization.

    Usage:
        # No need to call init() explicitly - auto-initializes on first use
        rows = await Database.fetch_all("SELECT * FROM table")

        # Optional: explicit init() if you need to check success beforehand
        await Database.init()  # Returns True/False

        # Cleanup (typically in finally block or at application shutdown)
        await Database.close()
    """

    _pool: asyncpg.Pool | None = None
    _enabled: bool = False
    _initialized: bool = False
    _init_lock: asyncio.Lock | None = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """Get or create lock for thread-safe initialization."""
        if cls._init_lock is None:
            cls._init_lock = asyncio.Lock()
        return cls._init_lock

    @classmethod
    async def init(cls, config_obj=None) -> bool:
        """Initialize PostgreSQL connection pool.

        Can be called explicitly, but not required - first database operation
        will auto-initialize if needed.

        Returns:
            True if database is available, False otherwise
        """
        if cls._pool is not None:
            return True

        async with cls._get_lock():
            # Double-check after acquiring lock
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
                cls._initialized = True

                # Test connection
                async with cls._pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")

                logger.info(f"PostgreSQL connected: {cfg.db.host}:{cfg.db.port}/{cfg.db.database}")
                return True
            except Exception as e:
                cls._enabled = False
                cls._initialized = True
                logger.error(f"PostgreSQL initialization failed: {e}")
                return False

    @classmethod
    async def _ensure_initialized(cls) -> bool:
        """Ensure database is initialized, auto-initialize if not.

        This is the key to automatic lazy loading - called by all
        database operation methods before attempting to use the pool.
        """
        if cls._pool is not None:
            return True

        # Auto-initialize without explicit init() call
        return await cls.init()

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
        await cls._ensure_initialized()
        if not cls.is_enabled():
            raise DatabaseError("Database not enabled")

        async with cls._pool.acquire() as conn:
            return await conn.execute(sql, *args)

    @classmethod
    async def fetch_one(cls, sql: str, *args) -> asyncpg.Record | None:
        """Fetch a single row."""
        await cls._ensure_initialized()
        if not cls.is_enabled():
            return None

        async with cls._pool.acquire() as conn:
            return await conn.fetchrow(sql, *args)

    @classmethod
    async def fetch_all(cls, sql: str, *args) -> list[asyncpg.Record]:
        """Fetch all rows."""
        await cls._ensure_initialized()
        if not cls.is_enabled():
            return []

        async with cls._pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    @classmethod
    async def fetchval(cls, sql: str, *args):
        """Fetch a single value."""
        await cls._ensure_initialized()
        if not cls.is_enabled():
            return None

        async with cls._pool.acquire() as conn:
            return await conn.fetchval(sql, *args)

    @classmethod
    async def execute_many(cls, sql: str, args_list: list) -> int:
        """Execute SQL with multiple parameter sets (batch insert/update).

        Note: asyncpg's executemany returns None, so we return len(args_list)
        to indicate how many statements were attempted.
        """
        await cls._ensure_initialized()
        if not cls.is_enabled():
            raise DatabaseError("Database not enabled")

        async with cls._pool.acquire() as conn:
            await conn.executemany(sql, args_list)
            return len(args_list)

    @classmethod
    def transaction(cls):
        """Get a transaction context manager.

        Usage:
            async with Database.transaction() as tx:
                await tx.execute("INSERT ...")
                await tx.execute("UPDATE ...")
        """
        if not cls.is_enabled():
            raise DatabaseError("Database not enabled")

        return _TransactionContext(cls._pool)

    @classmethod
    @asynccontextmanager
    async def session(cls, config_obj=None):
        """Async context manager that handles DB init/close lifecycle.

        Usage:
            async with Database.session(config) as db:
                rows = await db.fetch_all("SELECT * FROM table")
        """
        await cls.init(config_obj)
        try:
            yield cls
        finally:
            await cls.close()

    @classmethod
    def row_to_dict(cls, row: asyncpg.Record | None) -> dict | None:
        """Convert asyncpg Record to dict."""
        if row is None:
            return None
        return dict(row)
