"""Cache implementations - PostgreSQL UNLOGGED + File fallback."""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from .config import config
from .database import Database
from .interfaces.cache import CacheABC

logger = logging.getLogger(__name__)


class FileCache(CacheABC):
    """File-based cache for local fallback."""

    def __init__(self):
        self.file_path = config.data_dir / "cache.json"
        self._ensure_file()
        self._cache: dict[str, Any] = self._load()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w") as f:
                json.dump({}, f)

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.file_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save(self):
        with open(self.file_path, "w") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def get(self, key: str) -> Any | None:
        if key in self._cache:
            entry = self._cache[key]
            if entry["expire_at"] > time.time():
                return entry["data"]
            else:
                del self._cache[key]
                self._save()
        return None

    def set(self, key: str, data: Any, ttl: int):
        self._cache[key] = {"data": data, "expire_at": time.time() + ttl}
        self._save()

    def delete(self, key: str):
        if key in self._cache:
            del self._cache[key]
            self._save()

    def clear(self):
        self._cache = {}
        self._save()

    async def async_get(self, key: str) -> Any | None:
        return self.get(key)

    async def async_set(self, key: str, data: Any, ttl: int):
        self.set(key, data, ttl)

    async def async_delete(self, key: str):
        self.delete(key)

    async def async_clear(self):
        self.clear()


class PostgresCache(CacheABC):
    """PostgreSQL UNLOGGED table cache - high performance with TTL support."""

    def __init__(self):
        self._prefix = "fcli:"
        self._cleanup_interval = 300
        self._last_cleanup = 0
        self._lock = asyncio.Lock()

    def _make_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def _cleanup_expired(self):
        async with self._lock:
            current_time = time.time()
            if current_time - self._last_cleanup < self._cleanup_interval:
                return
            self._last_cleanup = current_time

            if not Database.is_enabled():
                return

            try:
                await Database.execute(
                    "DELETE FROM cache_entries WHERE expires_at < $1",
                    datetime.fromtimestamp(current_time, tz=timezone.utc),
                )
            except Exception as e:
                logger.debug(f"Cache cleanup failed: {e}")

    async def async_get(self, key: str) -> Any | None:
        if not Database.is_enabled():
            return None

        await self._cleanup_expired()

        try:
            full_key = self._make_key(key)
            row = await Database.fetch_one(
                """
                SELECT value, expires_at
                FROM cache_entries
                WHERE key = $1 AND expires_at > $2
                """,
                full_key,
                datetime.now(timezone.utc),
            )

            if row:
                return json.loads(row["value"])
            return None
        except Exception as e:
            logger.debug(f"Postgres cache get failed for key {key}: {e}")
            return None

    async def async_set(self, key: str, data: Any, ttl: int):
        if not Database.is_enabled():
            return

        try:
            full_key = self._make_key(key)
            expire_at = datetime.fromtimestamp(time.time() + ttl, tz=timezone.utc)
            json_data = json.dumps(data, ensure_ascii=False)

            await Database.execute(
                """
                INSERT INTO cache_entries (key, value, expires_at, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    expires_at = EXCLUDED.expires_at,
                    created_at = EXCLUDED.created_at
                """,
                full_key,
                json_data,
                expire_at,
                datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.debug(f"Postgres cache set failed for key {key}: {e}")

    async def async_delete(self, key: str):
        if not Database.is_enabled():
            return

        try:
            full_key = self._make_key(key)
            await Database.execute("DELETE FROM cache_entries WHERE key = $1", full_key)
        except Exception as e:
            logger.debug(f"Postgres cache delete failed for key {key}: {e}")

    async def async_clear(self):
        if not Database.is_enabled():
            return

        try:
            await Database.execute("DELETE FROM cache_entries WHERE key LIKE $1", f"{self._prefix}%")
        except Exception as e:
            logger.debug(f"Postgres cache clear failed: {e}")


class HybridCache(CacheABC):
    """Hybrid cache: PostgreSQL priority with automatic File fallback."""

    def __init__(self):
        self._file_cache = FileCache()
        self._postgres_cache: PostgresCache | None = None
        self._use_postgres = True
        self._postgres_available = False
        self._last_health_check = 0
        self._health_check_interval = 60

    async def _check_postgres_health(self) -> bool:
        current_time = time.time()

        if current_time - self._last_health_check < self._health_check_interval:
            return self._postgres_available

        self._last_health_check = current_time

        if not self._use_postgres:
            self._postgres_available = False
            return False

        if self._postgres_cache is None:
            self._postgres_cache = PostgresCache()

        try:
            if Database.is_enabled():
                await Database.fetch_one("SELECT 1")
                self._postgres_available = True
                logger.debug("PostgreSQL health check passed")
            else:
                self._postgres_available = False
        except Exception as e:
            logger.debug(f"PostgreSQL health check failed: {e}")
            self._postgres_available = False

        return self._postgres_available

    def get(self, key: str) -> Any | None:
        return self._file_cache.get(key)

    def set(self, key: str, data: Any, ttl: int):
        self._file_cache.set(key, data, ttl)

    def delete(self, key: str):
        self._file_cache.delete(key)

    def clear(self):
        self._file_cache.clear()

    async def async_get(self, key: str) -> Any | None:
        if await self._check_postgres_health() and self._postgres_cache:
            data = await self._postgres_cache.async_get(key)
            if data is not None:
                return data
            logger.debug(f"Postgres miss for key {key}, falling back to file cache")

        return self._file_cache.get(key)

    async def async_set(self, key: str, data: Any, ttl: int):
        self._file_cache.set(key, data, ttl)

        if await self._check_postgres_health() and self._postgres_cache:
            await self._postgres_cache.async_set(key, data, ttl)

    async def async_delete(self, key: str):
        self._file_cache.delete(key)
        if self._postgres_cache:
            await self._postgres_cache.async_delete(key)

    async def async_clear(self):
        self._file_cache.clear()
        if self._postgres_cache:
            await self._postgres_cache.async_clear()

    @property
    def is_postgres_available(self) -> bool:
        return self._postgres_available


cache = HybridCache()
