"""统一缓存模块 - PostgreSQL UNLOGGED 表实现

使用 PostgreSQL UNLOGGED 表替代 Redis，实现零额外依赖的缓存方案。
UNLOGGED 表不记录 WAL，写入性能接近内存表，重启后数据清空。
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from .config import config
from .database import Database

logger = logging.getLogger(__name__)


class BaseCache(ABC):
    """缓存抽象基类"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass

    @abstractmethod
    def set(self, key: str, data: Any, ttl: int):
        """设置缓存"""
        pass

    @abstractmethod
    def delete(self, key: str):
        """删除缓存"""
        pass

    @abstractmethod
    def clear(self):
        """清空缓存"""
        pass

    @abstractmethod
    async def async_get(self, key: str) -> Optional[Any]:
        """异步获取缓存"""
        pass

    @abstractmethod
    async def async_set(self, key: str, data: Any, ttl: int):
        """异步设置缓存"""
        pass


class FileCache(BaseCache):
    """文件缓存实现 - 作为本地降级方案"""

    def __init__(self):
        self.file_path = config.data_dir / "cache.json"
        self._ensure_file()
        self._cache: Dict[str, Any] = self._load()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w") as f:
                json.dump({}, f)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save(self):
        with open(self.file_path, "w") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def get(self, key: str) -> Optional[Any]:
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

    async def async_get(self, key: str) -> Optional[Any]:
        """异步获取 - 文件缓存使用同步实现"""
        return self.get(key)

    async def async_set(self, key: str, data: Any, ttl: int):
        """异步设置 - 文件缓存使用同步实现"""
        self.set(key, data, ttl)


class PostgresCache(BaseCache):
    """PostgreSQL UNLOGGED 表缓存实现

    使用 UNLOGGED 表作为高性能缓存，特点：
    - 不记录 WAL，写入性能接近内存表
    - 支持 TTL 自动过期清理
    - 支持 key 前缀命名空间
    - 数据库重启后数据清空（符合缓存语义）
    """

    def __init__(self):
        self._prefix = "fcli:"
        self._cleanup_interval = 300  # 5分钟清理一次过期数据
        self._last_cleanup = 0
        self._lock = asyncio.Lock()

    def _make_key(self, key: str) -> str:
        """生成带前缀的 key"""
        return f"{self._prefix}{key}"

    async def _cleanup_expired(self):
        """清理过期缓存数据"""
        async with self._lock:
            current_time = time.time()
            # 限制清理频率
            if current_time - self._last_cleanup < self._cleanup_interval:
                return
            self._last_cleanup = current_time

            if not Database.is_enabled():
                return

            try:
                await Database.execute("DELETE FROM cache_entries WHERE expire_at < $1", int(current_time))
            except Exception as e:
                logger.debug(f"Cache cleanup failed: {e}")

    def get(self, key: str) -> Optional[Any]:
        """同步获取 - 尝试从数据库获取（仅限已初始化的连接）"""
        # PostgreSQL 缓存主要面向异步操作
        # 同步模式下回退到文件缓存
        return None

    def set(self, key: str, data: Any, ttl: int):
        """同步设置 - PostgreSQL 缓存主要面向异步操作"""
        pass

    def delete(self, key: str):
        """同步删除 - PostgreSQL 缓存主要面向异步操作"""
        pass

    def clear(self):
        """同步清空 - PostgreSQL 缓存主要面向异步操作"""
        pass

    async def async_get(self, key: str) -> Optional[Any]:
        """异步获取缓存 - 从 PostgreSQL UNLOGGED 表"""
        if not Database.is_enabled():
            return None

        # 定期清理过期数据
        await self._cleanup_expired()

        try:
            full_key = self._make_key(key)
            row = await Database.fetch_one(
                """
                SELECT data, expire_at 
                FROM cache_entries 
                WHERE key = $1 AND expire_at > $2
                """,
                full_key,
                int(time.time()),
            )

            if row:
                return json.loads(row["data"])
            return None
        except Exception as e:
            logger.debug(f"Postgres cache get failed for key {key}: {e}")
            return None

    async def async_set(self, key: str, data: Any, ttl: int):
        """异步设置缓存 - 写入 PostgreSQL UNLOGGED 表"""
        if not Database.is_enabled():
            return

        try:
            full_key = self._make_key(key)
            expire_at = int(time.time()) + ttl
            json_data = json.dumps(data, ensure_ascii=False)

            # 使用 UPSERT 语义
            await Database.execute(
                """
                INSERT INTO cache_entries (key, data, expire_at, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (key) DO UPDATE SET
                    data = EXCLUDED.data,
                    expire_at = EXCLUDED.expire_at,
                    created_at = EXCLUDED.created_at
                """,
                full_key,
                json_data,
                expire_at,
                int(time.time()),
            )
        except Exception as e:
            logger.debug(f"Postgres cache set failed for key {key}: {e}")

    async def async_delete(self, key: str):
        """异步删除缓存"""
        if not Database.is_enabled():
            return

        try:
            full_key = self._make_key(key)
            await Database.execute("DELETE FROM cache_entries WHERE key = $1", full_key)
        except Exception as e:
            logger.debug(f"Postgres cache delete failed for key {key}: {e}")

    async def async_clear(self):
        """异步清空缓存（只清空带前缀的 key）"""
        if not Database.is_enabled():
            return

        try:
            await Database.execute("DELETE FROM cache_entries WHERE key LIKE $1", f"{self._prefix}%")
        except Exception as e:
            logger.debug(f"Postgres cache clear failed: {e}")


class HybridCache(BaseCache):
    """混合缓存：PostgreSQL UNLOGGED 表优先，自动降级到文件缓存

    初始化时会检测 PostgreSQL 是否可用，若不可用则自动使用文件缓存。
    即使 PostgreSQL 可用，也会同时写入文件缓存作为备份。
    """

    def __init__(self):
        self._file_cache = FileCache()
        self._postgres_cache: Optional[PostgresCache] = None
        self._use_postgres = True
        self._postgres_available = False
        self._last_health_check = 0
        self._health_check_interval = 60  # 健康检查间隔（秒）

    async def _check_postgres_health(self) -> bool:
        """检查 PostgreSQL 健康状态

        使用简单查询检测 PostgreSQL 是否可用。
        不会频繁检查，有 60 秒的间隔限制。

        Returns:
            True 如果 PostgreSQL 可用
        """
        current_time = time.time()

        # 限制检查频率
        if current_time - self._last_health_check < self._health_check_interval:
            return self._postgres_available

        self._last_health_check = current_time

        if not self._use_postgres:
            self._postgres_available = False
            return False

        # 延迟初始化 PostgreSQL 缓存客户端
        if self._postgres_cache is None:
            self._postgres_cache = PostgresCache()

        # 尝试连接并执行简单查询
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

    def get(self, key: str) -> Optional[Any]:
        """同步获取 - 使用文件缓存"""
        return self._file_cache.get(key)

    def set(self, key: str, data: Any, ttl: int):
        """同步设置 - 使用文件缓存"""
        self._file_cache.set(key, data, ttl)

    def delete(self, key: str):
        """同步删除"""
        self._file_cache.delete(key)

    def clear(self):
        """同步清空"""
        self._file_cache.clear()

    async def async_get(self, key: str) -> Optional[Any]:
        """异步获取 - 优先 PostgreSQL，降级到文件"""
        # 检查 PostgreSQL 健康状态
        if await self._check_postgres_health():
            data = await self._postgres_cache.async_get(key)
            if data is not None:
                return data
            # PostgreSQL 没有数据或获取失败，降级到文件缓存
            logger.debug(f"Postgres miss for key {key}, falling back to file cache")

        return self._file_cache.get(key)

    async def async_set(self, key: str, data: Any, ttl: int):
        """异步设置 - 同时写入 PostgreSQL 和文件"""
        # 始终写入文件缓存（作为备份）
        self._file_cache.set(key, data, ttl)

        # 尝试写入 PostgreSQL
        if await self._check_postgres_health():
            await self._postgres_cache.async_set(key, data, ttl)

    async def async_delete(self, key: str):
        """异步删除"""
        self._file_cache.delete(key)
        if self._postgres_cache:
            await self._postgres_cache.async_delete(key)

    async def async_clear(self):
        """异步清空"""
        self._file_cache.clear()
        if self._postgres_cache:
            await self._postgres_cache.async_clear()

    @property
    def is_postgres_available(self) -> bool:
        """返回 PostgreSQL 是否可用"""
        return self._postgres_available


# 全局缓存实例
cache = HybridCache()
