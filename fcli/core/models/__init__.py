"""Models package - unified data models."""

from .asset import Asset, ExchangeRate, Quote
from .base import AssetType, Market
from .fund import Fund, FundDetail, FundScale, FundSearchResult, FundType, InvestType
from .gold import GoldReserve
from .gold_supply_demand import GoldSupplyDemand
from .gpr import GPR_COUNTRY_NAMES, GPRHistory, GPRIndexType
from .log import WatchlistAssetDB

__all__ = [
    # Base types
    "Market",
    "AssetType",
    # Asset models
    "Asset",
    "Quote",
    "ExchangeRate",
    # Fund models
    "Fund",
    "FundDetail",
    "FundScale",
    "FundSearchResult",
    "FundType",
    "InvestType",
    # Gold models
    "GoldReserve",
    "GoldSupplyDemand",
    # GPR models
    "GPRHistory",
    "GPRIndexType",
    "GPR_COUNTRY_NAMES",
    # System models
    "WatchlistAssetDB",
]
