"""Interfaces package - abstract contracts for dependency injection.

This module provides both Protocol and ABC based interfaces:
- Protocol: Structural subtyping (duck typing with type checking)
- ABC: Nominal subtyping (explicit inheritance)

Use Protocol for flexibility, ABC when you need to enforce inheritance.
"""

from .database import IDatabase
from .http import HttpClientABC, IHttpClient
from .source import (
    DataSourceABC,
    ForexSourceABC,
    GoldSourceABC,
    GprSourceABC,
    # Base
    IDataSource,
    # Forex
    IForexSource,
    # Gold
    IGoldSource,
    # GPR
    IGprSource,
    # Quote
    IQuoteSource,
    QuoteSourceABC,
)
from .storage import IStorage, StorageABC

__all__ = [
    # HTTP Client
    "IHttpClient",
    "HttpClientABC",
    # Storage
    "IStorage",
    "StorageABC",
    # Database
    "IDatabase",
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
