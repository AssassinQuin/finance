"""Interfaces package - abstract contracts for dependency injection.

This module provides both Protocol and ABC based interfaces:
- Protocol: Structural subtyping (duck typing with type checking)
- ABC: Nominal subtyping (explicit inheritance)

Use Protocol for flexibility, ABC when you need to enforce inheritance.
"""

from .http import IHttpClient, HttpClientABC
from .storage import IStorage, StorageABC
from .source import (
    # Base
    IDataSource,
    DataSourceABC,
    # Quote
    IQuoteSource,
    QuoteSourceABC,
    # Gold
    IGoldSource,
    GoldSourceABC,
    # Forex
    IForexSource,
    ForexSourceABC,
    # GPR
    IGprSource,
    GprSourceABC,
)

__all__ = [
    # HTTP Client
    "IHttpClient",
    "HttpClientABC",
    # Storage
    "IStorage",
    "StorageABC",
    # Base Data Source
    "IDataSource",
    "DataSourceABC",
    # Quote Source
    "IQuoteSource",
    "QuoteSourceABC",
    # Gold Source
    "IGoldSource",
    "GoldSourceABC",
    # Forex Source
    "IForexSource",
    "ForexSourceABC",
    # GPR Source
    "IGprSource",
    "GprSourceABC",
]
