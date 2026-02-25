"""
SPDR Gold Trust 持仓数据服务
数据来源: AkShare (macro_cons_gold)
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..core.cache import cache
from ..core.config import config
from ..infra.http_client import http_client

logger = logging.getLogger(__name__)


@dataclass
class SPDRHolding:
    """SPDR 持仓数据"""
    date: str
    holdings: float  # 吨
    change: float  # 增减持
    value: float  # 美元


class SPDRService:
    """SPDR Gold Trust 持仓服务"""
    
    def __init__(self):
        self._cache_key = "spdr:holdings"
    
    async def get_holdings(self, days: int = 30) -> List[Dict]:
        """
        获取 SPDR 持仓历史数据
        
        Args:
            days: 获取最近多少天的数据
            
        Returns:
            List of holdings data
        """
        # 检查缓存
        cached = cache.get(self._cache_key)
        if cached:
            return cached[:days]
        
        try:
            import akshare as ak
        except ImportError:
            logger.error("AkShare 未安装")
            return []
        
        try:
            df = ak.macro_cons_gold()
            
            if df is None or df.empty:
                return []
            
            holdings = []
            for _, row in df.iterrows():
                try:
                    holdings.append({
                        "date": str(row["日期"])[:10],
                        "holdings": float(row["总库存"]),
                        "change": float(row["增持/减持"]) if row["增持/减持"] else 0.0,
                        "value": float(row["总价值"]) if row["总价值"] else 0.0,
                    })
                except Exception:
                    continue
            
            # 按日期倒序排列 (最新的在前)
            holdings.sort(key=lambda x: x["date"], reverse=True)
            
            # 缓存 1 小时
            cache.set(self._cache_key, holdings, 3600)
            
            return holdings[:days]
            
        except Exception as e:
            logger.error(f"Failed to fetch SPDR holdings: {e}")
            return []
    
    async def get_latest(self) -> Optional[Dict]:
        """获取最新的 SPDR 持仓"""
        holdings = await self.get_holdings(days=1)
        return holdings[0] if holdings else None
    
    async def get_summary(self) -> Dict:
        """
        获取 SPDR 持仓摘要
        
        Returns:
            包含最新持仓、变化趋势的摘要
        """
        holdings = await self.get_holdings(days=30)
        
        if not holdings:
            return {
                "latest": None,
                "change_1d": 0,
                "change_7d": 0,
                "change_30d": 0,
                "trend": "unknown",
            }
        
        latest = holdings[0]
        
        # 计算变化
        change_1d = holdings[1]["change"] if len(holdings) > 1 else 0
        
        change_7d = 0
        if len(holdings) >= 7:
            change_7d = latest["holdings"] - holdings[6]["holdings"]
        
        change_30d = 0
        if len(holdings) >= 30:
            change_30d = latest["holdings"] - holdings[29]["holdings"]
        
        # 判断趋势
        if change_7d > 5:
            trend = "increasing"
        elif change_7d < -5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "latest": latest,
            "change_1d": change_1d,
            "change_7d": change_7d,
            "change_30d": change_30d,
            "trend": trend,
            "history_7d": holdings[:7],
        }


spdr_service = SPDRService()
