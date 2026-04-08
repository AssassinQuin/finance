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


SOURCE_PBOC = "PBOC"
SOURCE_SAFE = "SAFE"
SOURCE_IMF = "IMF"
SOURCE_AKSHARE = "Akshare"
SOURCE_FRANKFURTER = "Frankfurter"
SOURCE_WGC = "WGC"

COUNTRY_CN_CODE = "CHN"
COUNTRY_CN_NAME = "中国"
