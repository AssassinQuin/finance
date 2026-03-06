"""Storage implementations - PostgreSQL + File fallback."""

import json
import os
import tempfile
from pathlib import Path

from .database import Database
from .interfaces.storage import StorageABC
from .models import Asset


class FileStorage(StorageABC):
    """File-based storage for watchlist assets (local fallback)."""

    def __init__(self):
        self.storage_dir = Path.home() / ".fcli"
        self.storage_file = self.storage_dir / "watchlist.json"
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write(self, data: dict):
        fd, temp_path = tempfile.mkstemp(dir=self.storage_dir, prefix="watchlist_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            os.replace(temp_path, self.storage_file)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _read_json(self) -> dict:
        if not self.storage_file.exists():
            return {"assets": []}
        try:
            with open(self.storage_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {"assets": []}

    async def load(self) -> list[Asset]:
        data = self._read_json()
        assets = []
        for asset_dict in data.get("assets", []):
            try:
                assets.append(Asset(**asset_dict))
            except Exception:
                continue
        return assets

    async def save(self, assets: list[Asset]):
        data = {"assets": [asset.model_dump() for asset in assets]}
        self._atomic_write(data)

    async def add(self, asset: Asset) -> bool:
        assets = await self.load()
        if any(a.code == asset.code for a in assets):
            return False
        assets.append(asset)
        await self.save(assets)
        return True

    async def remove(self, code: str) -> bool:
        assets = await self.load()
        original_count = len(assets)
        assets = [a for a in assets if a.code != code]
        if len(assets) < original_count:
            await self.save(assets)
            return True
        return False

    async def get(self, code: str) -> Asset | None:
        assets = await self.load()
        for asset in assets:
            if asset.code == code:
                return asset
        return None


class PostgresStorage(StorageABC):
    """PostgreSQL-based storage using WatchlistAssetStore."""

    def __init__(self):
        from .stores.watchlist import WatchlistAssetStore

        self._store = WatchlistAssetStore()

    async def load(self) -> list[Asset]:
        return await self._store.get_assets()

    async def save(self, assets: list[Asset]):
        for asset in assets:
            await self._store.add(asset)

    async def add(self, asset: Asset) -> bool:
        return await self._store.add(asset)

    async def remove(self, code: str) -> bool:
        return await self._store.remove(code)

    async def get(self, code: str) -> Asset | None:
        result = await self._store.get_by_code(code)
        if result:
            return Asset(
                code=result.code,
                market=result.market,
                type=result.type,
                api_code=result.api_code,
                name=result.name,
            )
        return None


class HybridStorage(StorageABC):
    """Hybrid storage: PostgreSQL priority with automatic File fallback."""

    def __init__(self):
        self._file_storage = FileStorage()
        self._postgres_storage: PostgresStorage | None = None
        self._postgres_available = False
        self._last_health_check = 0
        self._health_check_interval = 60
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized:
            return
        self._initialized = True
        await self._check_postgres_health()

    async def _check_postgres_health(self) -> bool:
        import time

        current_time = time.time()
        if current_time - self._last_health_check < self._health_check_interval:
            return self._postgres_available

        self._last_health_check = current_time

        try:
            if Database.is_enabled():
                await Database.fetch_one("SELECT 1")
                if self._postgres_storage is None:
                    self._postgres_storage = PostgresStorage()
                self._postgres_available = True
            else:
                self._postgres_available = False
        except Exception:
            self._postgres_available = False

        return self._postgres_available

    async def load(self) -> list[Asset]:
        await self._ensure_initialized()
        if await self._check_postgres_health() and self._postgres_storage:
            return await self._postgres_storage.load()
        return await self._file_storage.load()

    async def save(self, assets: list[Asset]):
        await self._ensure_initialized()
        if await self._check_postgres_health() and self._postgres_storage:
            await self._postgres_storage.save(assets)
        else:
            await self._file_storage.save(assets)

    async def add(self, asset: Asset) -> bool:
        await self._ensure_initialized()
        if await self._check_postgres_health() and self._postgres_storage:
            return await self._postgres_storage.add(asset)
        return await self._file_storage.add(asset)

    async def remove(self, code: str) -> bool:
        await self._ensure_initialized()
        if await self._check_postgres_health() and self._postgres_storage:
            return await self._postgres_storage.remove(code)
        return await self._file_storage.remove(code)

    async def get(self, code: str) -> Asset | None:
        await self._ensure_initialized()
        if await self._check_postgres_health() and self._postgres_storage:
            return await self._postgres_storage.get(code)
        return await self._file_storage.get(code)

    @property
    def is_postgres_available(self) -> bool:
        return self._postgres_available


storage = HybridStorage()
