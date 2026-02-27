"""Base store class with common database operations."""

from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
import aiomysql

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

        sql = f"SELECT * FROM {cls.table_name} WHERE {cls.pk_field} = %s"

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (id,))
                row = await cur.fetchone()
                return cls._row_to_model(row) if row else None

    @classmethod
    async def get_all(cls, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination."""
        if not cls._is_enabled():
            return []

        sql = f"SELECT * FROM {cls.table_name} LIMIT %s OFFSET %s"

        async with cls._pool().acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (limit, offset))
                rows = await cur.fetchall()
                return [cls._row_to_model(row) for row in rows]

    @classmethod
    async def delete_by_id(cls, id: int) -> bool:
        """Delete record by ID."""
        if not cls._is_enabled():
            return False

        sql = f"DELETE FROM {cls.table_name} WHERE {cls.pk_field} = %s"

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (id,))
                return cur.rowcount > 0

    @classmethod
    async def count(cls, where: str = "", params: tuple = ()) -> int:
        """Count records."""
        if not cls._is_enabled():
            return 0

        sql = f"SELECT COUNT(*) FROM {cls.table_name}"
        if where:
            sql += f" WHERE {where}"

        async with cls._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                result = await cur.fetchone()
                return result[0] if result else 0
