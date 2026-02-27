"""Base enums and types shared across models."""

from enum import Enum


class Market(str, Enum):
    """Market/region enumeration."""
    CN = "CN"       # A-share
    HK = "HK"       # Hong Kong
    US = "US"       # US Stocks
    FUND = "FUND"   # China Funds
    GLOBAL = "GLOBAL"  # Global Indices/Forex
    FOREX = "FOREX"
    BOND = "BOND"


class AssetType(str, Enum):
    """Asset type enumeration."""
    STOCK = "STOCK"
    FUND = "FUND"
    INDEX = "INDEX"
    FOREX = "FOREX"
    BOND = "BOND"
