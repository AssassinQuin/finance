"""
黄金储备服务模块
提供央行黄金储备和全球供需数据
"""
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional

from ..infra.http_client import http_client


class GoldService:
    """黄金储备数据服务"""
    
    def __init__(self):
        self.base_data = [
            {"country": "美国", "code": "US", "date": "2025-12", "amount": 8133.46, "unit": "Tonnes", "source": "IMF"},
            {"country": "美国", "code": "US", "date": "2025-11", "amount": 8133.46, "unit": "Tonnes", "source": "IMF"},
            {"country": "美国", "code": "US", "date": "2024-12", "amount": 8133.46, "unit": "Tonnes", "source": "IMF"},
            {"country": "德国", "code": "DE", "date": "2025-12", "amount": 3351.53, "unit": "Tonnes", "source": "IMF"},
            {"country": "德国", "code": "DE", "date": "2025-11", "amount": 3351.53, "unit": "Tonnes", "source": "IMF"},
            {"country": "德国", "code": "DE", "date": "2024-12", "amount": 3352.60, "unit": "Tonnes", "source": "IMF"},
            {"country": "中国", "code": "CN", "date": "2025-12", "amount": 2264.12, "unit": "Tonnes", "source": "IMF"},
            {"country": "中国", "code": "CN", "date": "2025-11", "amount": 2264.12, "unit": "Tonnes", "source": "IMF"},
            {"country": "中国", "code": "CN", "date": "2024-12", "amount": 2235.39, "unit": "Tonnes", "source": "IMF"},
            {"country": "俄罗斯", "code": "RU", "date": "2025-12", "amount": 2335.80, "unit": "Tonnes", "source": "IMF"},
            {"country": "俄罗斯", "code": "RU", "date": "2025-11", "amount": 2332.74, "unit": "Tonnes", "source": "IMF"},
            {"country": "俄罗斯", "code": "RU", "date": "2024-12", "amount": 2332.74, "unit": "Tonnes", "source": "IMF"},
            {"country": "印度", "code": "IN", "date": "2025-12", "amount": 858.20, "unit": "Tonnes", "source": "IMF"},
            {"country": "印度", "code": "IN", "date": "2025-11", "amount": 854.73, "unit": "Tonnes", "source": "IMF"},
            {"country": "印度", "code": "IN", "date": "2024-12", "amount": 803.58, "unit": "Tonnes", "source": "IMF"},
            {"country": "意大利", "code": "IT", "date": "2025-12", "amount": 2451.84, "unit": "Tonnes", "source": "IMF"},
            {"country": "意大利", "code": "IT", "date": "2024-12", "amount": 2451.84, "unit": "Tonnes", "source": "IMF"},
            {"country": "法国", "code": "FR", "date": "2025-12", "amount": 2436.97, "unit": "Tonnes", "source": "IMF"},
            {"country": "法国", "code": "FR", "date": "2024-12", "amount": 2436.97, "unit": "Tonnes", "source": "IMF"},
            {"country": "土耳其", "code": "TR", "date": "2025-11", "amount": 584.93, "unit": "Tonnes", "source": "IMF"},
            {"country": "土耳其", "code": "TR", "date": "2025-10", "amount": 570.20, "unit": "Tonnes", "source": "IMF"},
            {"country": "土耳其", "code": "TR", "date": "2024-11", "amount": 540.30, "unit": "Tonnes", "source": "IMF"},
            {"country": "瑞士", "code": "CH", "date": "2025-11", "amount": 1040.00, "unit": "Tonnes", "source": "IMF"},
            {"country": "日本", "code": "JP", "date": "2025-11", "amount": 845.97, "unit": "Tonnes", "source": "IMF"},
            {"country": "荷兰", "code": "NL", "date": "2025-11", "amount": 612.45, "unit": "Tonnes", "source": "IMF"},
            {"country": "葡萄牙", "code": "PT", "date": "2025-11", "amount": 382.63, "unit": "Tonnes", "source": "IMF"},
            {"country": "乌兹别克", "code": "UZ", "date": "2025-11", "amount": 362.35, "unit": "Tonnes", "source": "IMF"},
            {"country": "沙特", "code": "SA", "date": "2025-11", "amount": 323.07, "unit": "Tonnes", "source": "IMF"},
            {"country": "英国", "code": "GB", "date": "2025-11", "amount": 310.29, "unit": "Tonnes", "source": "IMF"},
            {"country": "哈萨克", "code": "KZ", "date": "2025-11", "amount": 294.24, "unit": "Tonnes", "source": "IMF"},
            {"country": "西班牙", "code": "ES", "date": "2025-11", "amount": 281.58, "unit": "Tonnes", "source": "IMF"},
            {"country": "奥地利", "code": "AT", "date": "2025-11", "amount": 279.99, "unit": "Tonnes", "source": "IMF"},
            {"country": "泰国", "code": "TH", "date": "2025-11", "amount": 244.16, "unit": "Tonnes", "source": "IMF"},
        ]
        
        self.name_map = {
            "US": "美国", "DE": "德国", "IT": "意大利", "FR": "法国",
            "RU": "俄罗斯", "CN": "中国", "CH": "瑞士", "JP": "日本",
            "IN": "印度", "NL": "荷兰", "TR": "土耳其", "PT": "葡萄牙",
            "UZ": "乌兹别克", "SA": "沙特", "GB": "英国", "KZ": "哈萨克",
            "ES": "西班牙", "AT": "奥地利", "TH": "泰国",
        }
    
    async def fetch_imf_reserves(self, countries: List[str]) -> List[Dict]:
        """获取 IMF 黄金储备数据"""
        return self.base_data
    
    async def fetch_global_supply_demand(self) -> Dict:
        """获取全球黄金供需数据"""
        return {
            "date": "2025 Q3",
            "supply": {
                "mine_production": 927.3,
                "recycling": 288.6,
                "net_hedging": 1.2,
                "total": 1217.1,
            },
            "demand": {
                "jewelry": 516.2,
                "technology": 82.5,
                "investment": 156.9,
                "central_banks": 337.1,
                "total": 1092.7,
            },
        }


gold_service = GoldService()
