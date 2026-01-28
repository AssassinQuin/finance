from typing import Dict, List, Type

from ..core.models import Asset, AssetType, Market
from .base import QuoteSource
from .eastmoney import EastMoneyFundSource, EastMoneyGlobalSource
from .sina import SinaSource


class SourceFactory:
    _instances: Dict[str, QuoteSource] = {}

    @classmethod
    def get_source(cls, asset: Asset) -> QuoteSource:
        """
        Dispatch asset to the correct source strategy based on market and type.
        """
        if asset.market == Market.CN and asset.type == AssetType.FUND:
            return cls._get_instance(EastMoneyFundSource)
        elif asset.market == Market.GLOBAL:
            return cls._get_instance(EastMoneyGlobalSource)
        else:
            # Default to Sina for Stocks (CN/HK/US) and other Indices
            return cls._get_instance(SinaSource)

    @classmethod
    def _get_instance(cls, source_cls: Type[QuoteSource]) -> QuoteSource:
        key = source_cls.__name__
        if key not in cls._instances:
            cls._instances[key] = source_cls()
        return cls._instances[key]
