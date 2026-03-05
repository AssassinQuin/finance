# PostgreSQL Migration Design & Development Document

## 1. Overview
This document outlines the architecture and development plan for migrating the `fcli` project to a pure PostgreSQL infrastructure ("Just Use Postgres"). The goal is to replace MySQL (relational data) and Redis (caching) with PostgreSQL and its extensions (e.g., UNLOGGED tables for cache), removing all legacy compatibility code and ensuring a robust, decoupled design.

## 2. Current State Analysis & Risk Assessment

### 2.1. Uncommitted Changes Analysis
- **Core Database (`core/database.py`)**: Replaced `aiomysql` with `asyncpg`.
- **Cache (`core/cache.py`)**: Implemented `PostgresCache` using UNLOGGED tables.
- **Migration Scripts**: Updated to generate PostgreSQL schema.

### 2.2. Identified Risks & Bugs
1.  **Argument Passing Bug in Cache**:
    - *Issue*: `PostgresCache` passes parameters as a tuple `(arg,)` to `Database.execute`, but `Database.execute` expects `*args`.
    - *Impact*: Runtime errors when setting/getting cache (e.g., `TypeError` or `PostgresSyntaxError`).
    - *Fix*: Unpack arguments or change `Database.execute` signature.

2.  **Return Type Mismatch**:
    - *Issue*: `Database.execute` type hint returns `int`, but `asyncpg` returns a command tag string (e.g., `"INSERT 0 1"`).
    - *Impact*: Code expecting an integer count (like `if result > 0`) will fail or behave unexpectedly.
    - *Fix*: Parse the command tag to return the actual row count, or update type hints and callers.

3.  **SQL Placeholder Syntax**:
    - *Issue*: MySQL uses `%s`, PostgreSQL uses `$1, $2`. `BaseStore` currently has a `_convert_placeholders` regex hack.
    - *Risk*: Regex replacement is fragile and may break on complex queries or string literals containing `%s`.
    - *Decision*: Remove compatibility hacks. Refactor all stores to use native `$n` syntax or a Query Builder (e.g., Pypika).

4.  **Hardcoded Dependencies**:
    - *Issue*: Services and Stores import the global `Database` class directly.
    - *Risk*: Makes unit testing difficult (requires patching globals) and couples business logic to the specific `asyncpg` implementation.

## 3. Architecture Design

### 3.1. Abstraction Layer
To ensure future switchability (e.g., to SQLite for local dev or another DB), we introduce abstract interfaces.

```python
from typing import Protocol, Any, List, Optional

class DatabaseInterface(Protocol):
    async def execute(self, query: str, *args: Any) -> int: ...
    async def fetch_one(self, query: str, *args: Any) -> Optional[dict]: ...
    async def fetch_all(self, query: str, *args: Any) -> List[dict]: ...
    async def transaction(self): ...
```

### 3.2. Cache Abstraction
The cache system should be agnostic of the backing store.

```python
class CacheInterface(Protocol):
    async def get(self, key: str) -> Optional[Any]: ...
    async def set(self, key: str, value: Any, ttl: int = 300): ...
    async def delete(self, key: str): ...
```

### 3.3. Database Implementation (PostgreSQL)
- **Driver**: `asyncpg` (high performance).
- **Connection Pool**: Managed via `asyncpg.create_pool`.
- **Row Factory**: Convert `asyncpg.Record` to `dict` automatically at the driver level or adapter level.
- **Placeholders**: Native `$1, $2`.

### 3.4. Cache Implementation (PostgreSQL UNLOGGED Tables)
- **Schema**:
  ```sql
  CREATE UNLOGGED TABLE IF NOT EXISTS cache_entries (
      key TEXT PRIMARY KEY,
      data JSONB NOT NULL,
      expires_at TIMESTAMP NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at);
  ```
- **Cleanup Strategy**:
  - Lazy expiration on read.
  - Periodic background cleanup (e.g., using `pg_cron` extension if available, or application-side scheduled task).

## 4. Refactoring Plan

### Phase 1: Core Infrastructure Fixes (Immediate)
1.  **Fix `Database.execute`**: Ensure it returns `int` by parsing `asyncpg`'s return string.
2.  **Fix `PostgresCache`**: Correct argument passing to `Database.execute`.
3.  **Standardize Types**: Ensure `fetch_all` returns `List[dict]`, not `List[Record]`.

### Phase 2: Decoupling & Interfaces
1.  Define `DatabaseInterface` in `fcli/core/interfaces/storage.py`.
2.  Refactor `Database` class to implement this interface.
3.  Inject dependencies into Stores/Services instead of using global `Database`.

### Phase 3: "Clean Break" from MySQL
1.  **Remove `_convert_placeholders`**: Delete compatibility code in `BaseStore`.
2.  **Update Stores**: Rewrite all SQL queries in `QuoteStore`, `GoldStore`, etc., to use `$1` syntax.
3.  **Data Migration**:
    - Since "no compatibility/dual-write" is required, we provide a clean schema init script.
    - `migrate.py` should handle `DROP TABLE` and clean `CREATE TABLE` for Postgres.

## 5. Development Guidelines

### 5.1. SQL Standards
- Use **UPPERCASE** for SQL keywords.
- Use `$n` for parameters. NEVER string formatting.
- Use `JSONB` for unstructured data.
- Use `TIMESTAMPTZ` (Timestamp with time zone) where possible, or consistent UTC `TIMESTAMP`.

### 5.2. Error Handling
- Wrap `asyncpg` exceptions (e.g., `UniqueViolationError`) into application-specific `StorageError` or `DuplicateError`.
- Ensure connections are released back to the pool in `finally` blocks (handled by `async with pool.acquire()` context manager).

### 5.3. Testing
- Use `pytest-asyncio`.
- Use a local Docker PostgreSQL container for integration tests.
- Mock `DatabaseInterface` for unit tests of Services.

## 6. Migration Checklist
- [ ] Fix `Database.execute` return value.
- [ ] Fix `PostgresCache` argument bug.
- [ ] Remove `_convert_placeholders` from `BaseStore`.
- [ ] Update all Stores to use `$1` placeholders.
- [ ] Verify `docker-compose.yml` uses `postgres:15-alpine`.
- [ ] Verify `migrate.py` creates tables with correct Postgres types (`SERIAL`, `JSONB`, `TIMESTAMPTZ`).
