"""Database interface definitions."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IDatabase(Protocol):
    """Protocol for database implementations.

    Provides abstraction over database operations for future
    switchability (e.g., to SQLite for local dev).
    """

    async def execute(self, sql: str, *args: Any) -> int:
        """Execute a SQL statement.

        Args:
            sql: SQL statement with $1, $2 placeholders
            *args: Parameters for the statement

        Returns:
            Number of rows affected
        """
        ...

    async def fetch_one(self, sql: str, *args: Any) -> dict | None:
        """Fetch a single row.

        Args:
            sql: SQL query with $1, $2 placeholders
            *args: Parameters for the query

        Returns:
            Row as dict, or None if not found
        """
        ...

    async def fetch_all(self, sql: str, *args: Any) -> list[dict]:
        """Fetch all rows.

        Args:
            sql: SQL query with $1, $2 placeholders
            *args: Parameters for the query

        Returns:
            List of rows as dicts
        """
        ...

    async def fetchval(self, sql: str, *args: Any) -> Any:
        """Fetch a single value.

        Args:
            sql: SQL query with $1, $2 placeholders
            *args: Parameters for the query

        Returns:
            Single value, or None if not found
        """
        ...

    def is_enabled(self) -> bool:
        """Check if database is enabled and available."""
        ...
