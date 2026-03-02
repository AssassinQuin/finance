"""Storage layer - database with JSON fallback."""

import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from .config import config
from .database import Database
from .models import Asset
from .stores import WatchlistAssetStore


class JSONStorage:
    """JSON file-based storage for watchlist assets (fallback mode)."""
    
    def __init__(self):
        # Store in user's home directory under .fcli
        self.storage_dir = Path.home() / ".fcli"
        self.storage_file = self.storage_dir / "watchlist.json"
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """Ensure storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _atomic_write(self, data: dict):
        """Atomically write data to JSON file.
        
        Uses temp file + rename pattern for crash safety.
        """
        # Write to temp file first
        fd, temp_path = tempfile.mkstemp(
            dir=self.storage_dir,
            prefix="watchlist_",
            suffix=".tmp"
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Atomic rename
            os.replace(temp_path, self.storage_file)
        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    def _read_json(self) -> dict:
        """Read JSON file safely."""
        if not self.storage_file.exists():
            return {"assets": []}
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Return empty data if file is corrupted
            return {"assets": []}
    
    async def load(self) -> List[Asset]:
        """Load assets from JSON file."""
        data = self._read_json()
        assets = []
        for asset_dict in data.get("assets", []):
            try:
                assets.append(Asset(**asset_dict))
            except Exception:
                # Skip invalid entries
                continue
        return assets
    
    async def save(self, assets: List[Asset]):
        """Save assets to JSON file."""
        data = {
            "assets": [asset.model_dump() for asset in assets]
        }
        self._atomic_write(data)
    
    async def add(self, asset: Asset) -> bool:
        """Add asset to JSON watchlist."""
        assets = await self.load()
        
        # Check if already exists
        if any(a.code == asset.code for a in assets):
            return False
        
        assets.append(asset)
        await self.save(assets)
        return True
    
    async def remove(self, code: str) -> bool:
        """Remove asset from JSON watchlist."""
        assets = await self.load()
        original_count = len(assets)
        
        assets = [a for a in assets if a.code != code]
        
        if len(assets) < original_count:
            await self.save(assets)
            return True
        return False
    
    async def get(self, code: str) -> Optional[Asset]:
        """Get asset by code from JSON watchlist."""
        assets = await self.load()
        for asset in assets:
            if asset.code == code:
                return asset
        return None


class Storage:
    """Hybrid storage - database with automatic JSON fallback."""

    _initialized = False
    _json_storage: Optional[JSONStorage] = None
    
    async def _ensure_db(self):
        """Ensure database is initialized."""
        if not Storage._initialized:
            await Database.init(config)
            Storage._initialized = True
            
            # Initialize JSON storage if DB is not available
            if not Database.is_enabled():
                if Storage._json_storage is None:
                    Storage._json_storage = JSONStorage()
    
    async def load(self) -> List[Asset]:
        """Load all active assets from database or JSON fallback."""
        await self._ensure_db()
        
        if Database.is_enabled():
            return await WatchlistAssetStore.get_assets()
        elif Storage._json_storage:
            return await Storage._json_storage.load()
        
        return []

    async def save(self, assets: List[Asset]):
        """Save assets to database or JSON fallback."""
        await self._ensure_db()
        
        if Database.is_enabled():
            for asset in assets:
                await WatchlistAssetStore.add(asset)
        elif Storage._json_storage:
            await Storage._json_storage.save(assets)

    async def add(self, asset: Asset) -> bool:
        """Add asset to watchlist."""
        await self._ensure_db()
        
        if Database.is_enabled():
            return await WatchlistAssetStore.add(asset)
        elif Storage._json_storage:
            return await Storage._json_storage.add(asset)
        
        return False

    async def remove(self, code: str) -> bool:
        """Remove asset from watchlist."""
        await self._ensure_db()
        
        if Database.is_enabled():
            return await WatchlistAssetStore.remove(code)
        elif Storage._json_storage:
            return await Storage._json_storage.remove(code)
        
        return False

    async def get(self, code: str) -> Optional[Asset]:
        """Get asset by code."""
        await self._ensure_db()
        
        if Database.is_enabled():
            return await WatchlistAssetStore.get_by_code(code)
        elif Storage._json_storage:
            return await Storage._json_storage.get(code)
        
        return None


storage = Storage()
