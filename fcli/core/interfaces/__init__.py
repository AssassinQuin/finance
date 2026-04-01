"""Interfaces package - abstract contracts for dependency injection."""

from .cache import CacheABC
from .database import DatabaseABC
from .http import HttpClientABC
from .source import (
    DataSourceABC,
    ForexSourceABC,
    GoldSourceABC,
    GprSourceABC,
    QuoteSourceABC,
)
from .storage import StorageABC

__all__ = [
    "CacheABC",
    "DatabaseABC",
    "HttpClientABC",
    "StorageABC",
    "DataSourceABC",
    "QuoteSourceABC",
    "GoldSourceABC",
    "ForexSourceABC",
    "GprSourceABC",
]
