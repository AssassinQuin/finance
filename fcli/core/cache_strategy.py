"""缓存策略抽象层

提供基于资产类型的动态TTL策略，支持：
- 不同资产类型使用不同缓存时长
- 交易时段/非交易时段差异化TTL
- 可配置的缓存策略映射
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Protocol

from .models.base import Market, AssetType


class ICacheStrategy(Protocol):
    """缓存策略协议"""

    def get_ttl(
        self, asset_type: AssetType, market: Optional[Market] = None, check_time: Optional[datetime] = None
    ) -> int:
        """获取缓存TTL（秒）

        Args:
            asset_type: 资产类型
            market: 市场（可选，用于交易时段判断）
            check_time: 检查时间（可选，默认当前时间）

        Returns:
            TTL 秒数
        """
        ...


class CacheStrategyBase(ABC):
    """缓存策略抽象基类"""

    @abstractmethod
    def get_ttl(
        self, asset_type: AssetType, market: Optional[Market] = None, check_time: Optional[datetime] = None
    ) -> int:
        """获取缓存TTL（秒）"""
        pass


class AssetTypeCacheStrategy(CacheStrategyBase):
    """
    基于资产类型的缓存策略

    TTL 配置策略：
    - STOCK/FUND/INDEX: 交易时段短缓存，非交易时段长缓存
    - GOLD: 按天缓存（黄金储备数据月度更新）
    - FOREX: 中等缓存（汇率日内波动）
    - BOND: 长缓存（债券数据更新频率低）
    """

    # 默认TTL配置（秒）
    DEFAULT_TTLS = {
        AssetType.STOCK: {
            "trading": 30,  # 交易时段 30秒
            "non_trading": 300,  # 非交易时段 5分钟
        },
        AssetType.FUND: {
            "trading": 60,  # 基金交易时段 1分钟
            "non_trading": 300,  # 非交易时段 5分钟
        },
        AssetType.INDEX: {
            "trading": 30,  # 指数交易时段 30秒
            "non_trading": 300,  # 非交易时段 5分钟
        },
        AssetType.FOREX: {
            "default": 3600,  # 外汇 1小时
        },
        AssetType.BOND: {
            "default": 7200,  # 债券 2小时
        },
    }

    # 黄金数据按天缓存（月度发布）
    GOLD_TTL = 86400  # 1天

    def __init__(
        self,
        stock_trading_ttl: int = 30,
        stock_non_trading_ttl: int = 300,
        fund_trading_ttl: int = 60,
        fund_non_trading_ttl: int = 300,
        index_trading_ttl: int = 30,
        index_non_trading_ttl: int = 300,
        forex_ttl: int = 3600,
        bond_ttl: int = 7200,
        gold_ttl: int = 86400,
    ):
        """初始化缓存策略

        Args:
            stock_trading_ttl: 股票交易时段TTL
            stock_non_trading_ttl: 股票非交易时段TTL
            fund_trading_ttl: 基金交易时段TTL
            fund_non_trading_ttl: 基金非交易时段TTL
            index_trading_ttl: 指数交易时段TTL
            index_non_trading_ttl: 指数非交易时段TTL
            forex_ttl: 外汇TTL
            bond_ttl: 债券TTL
            gold_ttl: 黄金TTL
        """
        self._ttls = {
            AssetType.STOCK: {
                "trading": stock_trading_ttl,
                "non_trading": stock_non_trading_ttl,
            },
            AssetType.FUND: {
                "trading": fund_trading_ttl,
                "non_trading": fund_non_trading_ttl,
            },
            AssetType.INDEX: {
                "trading": index_trading_ttl,
                "non_trading": index_non_trading_ttl,
            },
            AssetType.FOREX: {
                "default": forex_ttl,
            },
            AssetType.BOND: {
                "default": bond_ttl,
            },
        }
        self._gold_ttl = gold_ttl

    def get_ttl(
        self, asset_type: AssetType, market: Optional[Market] = None, check_time: Optional[datetime] = None
    ) -> int:
        """获取缓存TTL

        Args:
            asset_type: 资产类型
            market: 市场（用于交易时段判断）
            check_time: 检查时间

        Returns:
            TTL 秒数
        """
        # 黄金数据特殊处理（按天缓存）
        if asset_type == AssetType.STOCK and market == Market.GLOBAL:
            # 全球指数（如黄金指数）使用较长缓存
            return self._gold_ttl

        # 获取该资产类型的TTL配置
        ttl_config = self._ttls.get(asset_type)

        if ttl_config is None:
            # 未知资产类型，使用默认值
            return 300

        # 如果有交易时段配置且提供了市场信息
        if "trading" in ttl_config and market is not None:
            from ..utils.time_util import is_trading_hours

            if check_time is None:
                check_time = datetime.now()

            in_trading = is_trading_hours(market, check_time)
            return ttl_config["trading"] if in_trading else ttl_config["non_trading"]

        # 使用默认TTL
        return ttl_config.get("default", 300)

    @classmethod
    def from_config(cls, config) -> "AssetTypeCacheStrategy":
        """从配置创建缓存策略实例

        Args:
            config: 配置对象（需要有 cache 属性）

        Returns:
            缓存策略实例
        """
        return cls(
            stock_trading_ttl=getattr(config.cache, "stock_trading_ttl", 30),
            stock_non_trading_ttl=getattr(config.cache, "stock_non_trading_ttl", 300),
            fund_trading_ttl=getattr(config.cache, "fund_trading_ttl", 60),
            fund_non_trading_ttl=getattr(config.cache, "fund_non_trading_ttl", 300),
            index_trading_ttl=getattr(config.cache, "index_trading_ttl", 30),
            index_non_trading_ttl=getattr(config.cache, "index_non_trading_ttl", 300),
            forex_ttl=getattr(config.cache, "forex_ttl", 3600),
            bond_ttl=getattr(config.cache, "bond_ttl", 7200),
            gold_ttl=getattr(config.cache, "gold_ttl", 86400),
        )


# 默认缓存策略实例
default_cache_strategy = AssetTypeCacheStrategy()
