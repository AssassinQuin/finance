from pathlib import Path
from typing import Any, Dict

import toml


class Config:
    _instance = None
    _data: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        config_path = Path("config.toml")
        if config_path.exists():
            self._data = toml.load(config_path)
        else:
            # Defaults
            self._data = {
                "general": {"data_dir": "./data", "timeout": 10},
                "cache": {
                    "search_ttl": 86400,
                    "quote_short_ttl": 300,
                    "quote_long_ttl": 3600,
                },
            }

    @property
    def data_dir(self) -> Path:
        # Resolve path relative to project root
        # This file is in fcli/core/config.py, so root is 3 levels up?
        # No, fcli is a package.
        # Structure:
        # project_root/
        #   fcli/
        #     core/
        #       config.py
        #   data/
        
        # If user configured an absolute path, use it
        path_str = self._data["general"]["data_dir"]
        path = Path(path_str)
        if path.is_absolute():
            return path
            
        # Otherwise, resolve relative to project root
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        return project_root / path_str

    @property
    def timeout(self) -> int:
        return self._data["general"]["timeout"]

    @property
    def search_ttl(self) -> int:
        return self._data["cache"]["search_ttl"]

    @property
    def quote_short_ttl(self) -> int:
        return self._data["cache"]["quote_short_ttl"]

    @property
    def quote_long_ttl(self) -> int:
        return self._data["cache"]["quote_long_ttl"]


config = Config()
