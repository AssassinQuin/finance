"""Store classes for data access layer."""

from .exchange_rate import ExchangeRateFactStore, ExchangeRateStore
from .fund import FundStore
from .gold import GoldReserveStore, GoldStore
from .gold_supply_demand import GoldSupplyDemandStore
from .gpr import GPRHistoryStore
from .quote import QuoteFactStore, QuoteStore
from .watchlist import WatchlistAssetStore

__all__ = [
    "ExchangeRateFactStore",
    "ExchangeRateStore",
    "FundStore",
    "GoldReserveStore",
    "GoldStore",
    "GoldSupplyDemandStore",
    "GPRHistoryStore",
    "QuoteFactStore",
    "QuoteStore",
    "WatchlistAssetStore",
]
