"""Store classes for data access layer."""

from .exchange_rate import ExchangeRateStore
from .fund import FundStore
from .gold import GoldReserveStore, GoldStore
from .gold_supply_demand import GoldSupplyDemandStore
from .gpr import GPRHistoryStore
from .quote import QuoteStore
from .watchlist import WatchlistAssetStore

__all__ = [
    "ExchangeRateStore",
    "FundStore",
    "GoldReserveStore",
    "GoldStore",
    "GoldSupplyDemandStore",
    "GPRHistoryStore",
    "QuoteStore",
    "WatchlistAssetStore",
]
