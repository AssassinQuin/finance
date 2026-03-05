"""Base store class with common database operations."""

from typing import TypeVar, Generic, Type, List, Optional, Dict

from ..database import Database

T = TypeVar("T")


class BaseStore(Generic[T]):
    """Base class for database stores with common CRUD operations."""

    table_name: str
    model_class: Type[T]
    pk_field: str = "id"

    @classmethod
    def _pool(cls):
        """Get database pool."""
        return Database.get_pool()

    @classmethod
    def _is_enabled(cls) -> bool:
        """Check if database is enabled."""
        return Database.is_enabled()

    @classmethod
    def _row_to_model(cls, row: Dict) -> T:
        """Convert database row to model. Override in subclass."""
        raise NotImplementedError

    @classmethod
    async def get_by_id(cls, id: int) -> Optional[T]:
        """Get single record by ID."""
        if not cls._is_enabled():
            return None

        sql = f"SELECT * FROM {cls.table_name} WHERE {cls.pk_field} = $1"

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, id)
            return cls._row_to_model(dict(row)) if row else None

    @classmethod
    async def get_all(cls, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination."""
        if not cls._is_enabled():
            return []

        sql = f"SELECT * FROM {cls.table_name} LIMIT $1 OFFSET $2"

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, limit, offset)
            return [cls._row_to_model(dict(row)) for row in rows]

    @classmethod
    async def delete_by_id(cls, id: int) -> bool:
        """Delete record by ID."""
        if not cls._is_enabled():
            return False

        sql = f"DELETE FROM {cls.table_name} WHERE {cls.pk_field} = $1"

        pool = cls._pool()
        if not pool:
            return False

        async with pool.acquire() as conn:
            result = await conn.execute(sql, id)
            return result != "DELETE 0"

    @classmethod
    async def count(cls, where: str = "", *params) -> int:
        """Count records.

        Args:
            where: WHERE clause with $1, $2 placeholders (without WHERE keyword)
            *params: Parameters for the WHERE clause
        """
        if not cls._is_enabled():
            return 0

        sql = f"SELECT COUNT(*) FROM {cls.table_name}"
        if where:
            sql += f" WHERE {where}"

        pool = cls._pool()
        if not pool:
            return 0

        async with pool.acquire() as conn:
            result = await conn.fetchval(sql, *params)
            return result or 0
