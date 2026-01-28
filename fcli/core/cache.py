import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .config import config


class Cache:
    def __init__(self):
        self.file_path = config.data_dir / "cache.json"
        self._ensure_file()
        self._cache: Dict[str, Any] = self._load()

    def _ensure_file(self):
        if not self.file_path.exists():
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

    def clear(self):
        self._cache = {}
        self._save()


cache = Cache()
