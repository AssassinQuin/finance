import json
from pathlib import Path
from typing import List, Optional

from .config import config
from .models import Asset


class Storage:
    def __init__(self):
        self.file_path = config.data_dir / "assets.json"
        self._ensure_file()

    def _ensure_file(self):
        if not config.data_dir.exists():
            config.data_dir.mkdir(parents=True)
        if not self.file_path.exists():
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def load(self) -> List[Asset]:
        with open(self.file_path, "r") as f:
            data = json.load(f)
            return [Asset(**item) for item in data]

    def save(self, assets: List[Asset]):
        with open(self.file_path, "w") as f:
            # Sort by added_at
            assets.sort(key=lambda x: x.added_at)
            json.dump(
                [asset.model_dump(mode="json") for asset in assets],
                f,
                indent=2,
                ensure_ascii=False,
            )

    def add(self, asset: Asset):
        assets = self.load()
        # Check if exists (by code)
        for i, a in enumerate(assets):
            if a.code == asset.code:
                assets[i] = asset  # Update
                self.save(assets)
                return
        assets.append(asset)
        self.save(assets)

    def remove(self, code: str) -> bool:
        assets = self.load()
        initial_len = len(assets)
        assets = [a for a in assets if a.code != code]
        if len(assets) < initial_len:
            self.save(assets)
            return True
        return False

    def get(self, code: str) -> Optional[Asset]:
        assets = self.load()
        for a in assets:
            if a.code == code:
                return a
        return None


storage = Storage()
