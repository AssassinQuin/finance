"""统一缓存模块

支持 Redis 缓存和文件缓存，自动降级。
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from .config import config

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
    """文件缓存实现"""

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


class RedisCache(BaseCache):
    """Redis 缓存实现"""

    def __init__(self):
        self._pool = None
        self._redis = None
        self._connected = False
        self._prefix = config.redis.prefix

    async def _connect(self) -> bool:
        """连接 Redis"""
        if self._connected:
            return True

        try:
            import redis.asyncio as aioredis

            self._pool = aioredis.ConnectionPool(
                host=config.redis.host,
                port=config.redis.port,
                password=config.redis.password if config.redis.password else None,
                db=config.redis.db,
                max_connections=config.redis.pool_size,
                decode_responses=True,
            )
            self._redis = aioredis.Redis(connection_pool=self._pool)
            await self._redis.ping()
            self._connected = True
            logger.info(f"Redis connected: {config.redis.host}:{config.redis.port}")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False
            return False

    async def _disconnect(self):
        """断开 Redis 连接"""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()
        self._connected = False

    def _make_key(self, key: str) -> str:
        """生成带前缀的 key"""
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """同步获取 - Redis 不支持同步操作，返回 None"""
        logger.warning("Redis cache does not support sync get, use async_get instead")
        return None

    def set(self, key: str, data: Any, ttl: int):
        """同步设置 - Redis 不支持同步操作"""
        logger.warning("Redis cache does not support sync set, use async_set instead")

    def delete(self, key: str):
        """同步删除 - Redis 不支持同步操作"""
        logger.warning("Redis cache does not support sync delete")

    def clear(self):
        """同步清空 - Redis 不支持同步操作"""
        logger.warning("Redis cache does not support sync clear")

    async def async_get(self, key: str) -> Optional[Any]:
        """异步获取缓存"""
        if not self._connected and not await self._connect():
            return None

        try:
            full_key = self._make_key(key)
            data = await self._redis.get(full_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Redis get failed for key {key}: {e}")
            self._connected = False
            return None

    async def async_set(self, key: str, data: Any, ttl: int):
        """异步设置缓存"""
        if not self._connected and not await self._connect():
            return

        try:
            full_key = self._make_key(key)
            await self._redis.setex(full_key, ttl, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Redis set failed for key {key}: {e}")
            self._connected = False

    async def async_delete(self, key: str):
        """异步删除缓存"""
        if not self._connected and not await self._connect():
            return

        try:
            full_key = self._make_key(key)
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Redis delete failed for key {key}: {e}")
            self._connected = False

    async def async_clear(self):
        """异步清空缓存"""
        if not self._connected and not await self._connect():
            return

        try:
            # 只删除带前缀的 key
            keys = await self._redis.keys(f"{self._prefix}*")
            if keys:
                await self._redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}")
            self._connected = False


class HybridCache(BaseCache):
    """混合缓存：Redis 优先，自动降级到文件缓存"""

    def __init__(self):
        self._file_cache = FileCache()
        self._redis_cache: Optional[RedisCache] = None
        self._use_redis = config.redis.enabled
        self._redis_failed = False

        if self._use_redis:
            self._redis_cache = RedisCache()

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
        """异步获取 - 优先 Redis，降级到文件"""
        if self._use_redis and not self._redis_failed and self._redis_cache:
            data = await self._redis_cache.async_get(key)
            if data is not None:
                return data
            # Redis 获取失败，降级到文件缓存
            self._redis_failed = True
            logger.info("Redis unavailable, falling back to file cache")

        return self._file_cache.get(key)

    async def async_set(self, key: str, data: Any, ttl: int):
        """异步设置 - 同时写入 Redis 和文件"""
        # 始终写入文件缓存（作为备份）
        self._file_cache.set(key, data, ttl)

        # 尝试写入 Redis
        if self._use_redis and self._redis_cache:
            await self._redis_cache.async_set(key, data, ttl)

    async def async_delete(self, key: str):
        """异步删除"""
        self._file_cache.delete(key)
        if self._use_redis and self._redis_cache:
            await self._redis_cache.async_delete(key)

    async def async_clear(self):
        """异步清空"""
        self._file_cache.clear()
        if self._use_redis and self._redis_cache:
            await self._redis_cache.async_clear()


# 全局缓存实例
cache = HybridCache()
