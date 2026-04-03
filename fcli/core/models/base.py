"""Base enums and types shared across models."""

from enum import Enum


class Market(str, Enum):
    """Market/region enumeration."""

    CN = "CN"
    HK = "HK"
    US = "US"
    GLOBAL = "GLOBAL"


class AssetType(str, Enum):
    """Asset type enumeration."""

    STOCK = "STOCK"
    FUND = "FUND"
    INDEX = "INDEX"
    FOREX = "FOREX"
    BOND = "BOND"
    GOLD = "GOLD"
