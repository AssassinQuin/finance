"""
AkShare 数据源爬虫 - 中国黄金储备历史数据
完全在线查询，不依赖本地缓存
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from .base import BaseScraper, ScraperResult
from ...core.models import GoldReserve

logger = logging.getLogger(__name__)


class AkShareScraper(BaseScraper):
    """
    AkShare 数据源爬虫

    使用 AkShare 库获取中国官方黄金储备数据
    数据来源: 中国人民银行 / 国家外汇管理局
    """

    def __init__(self):
        super().__init__()
        self._source_name = "AkShare"

    @property
    def source_name(self) -> str:
        return self._source_name

    async def fetch(self) -> Any:
        """
        从 AkShare 获取中国黄金储备历史数据

        Returns:
            dict: {"type": "akshare", "data": [...]}
        """
        try:
            import akshare as ak
            import pandas as pd
        except ImportError:
            logger.error("AkShare 未安装，请运行: pip install akshare")
            return None

        try:
            logger.info("Fetching China gold reserves from AkShare...")

            # 获取中国外汇和黄金储备数据
            df = ak.macro_china_fx_gold()

            if df is None or df.empty:
                logger.warning("AkShare returned empty data")
                return None

            # 转换数据格式
            all_data = []
            for _, row in df.iterrows():
                try:
                    date_str = str(row.get("月份", ""))
                    gold_reserves = row.get("黄金储备-数值", 0)

                    # 跳过无效数据 (NaN 或空值)
                    import math

                    if gold_reserves is None or (isinstance(gold_reserves, float) and math.isnan(gold_reserves)):
                        continue

                    if not gold_reserves or float(gold_reserves) <= 0:
                        continue

                    # 解析日期 (格式: "2024年01月份")
                    parsed_date = self._parse_date(date_str)
                    if not parsed_date:
                        continue

                    # 万盎司转换为吨 (从配置读取转换系数)
                    from fcli.core.config import config

                    amount_tonnes = float(gold_reserves) * config.gold.wan_oz_to_tonne
                    all_data.append(
                        {
                            "country_code": "CHN",
                            "country_name": "中国",
                            "amount": round(amount_tonnes, 2),
                            "date": parsed_date,
                        }
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse row: {e}")
                    continue

            if not all_data:
                logger.warning("No valid data parsed from AkShare")
                return None

            # 按日期排序，最新的在前
            all_data.sort(key=lambda x: x["date"], reverse=True)

            logger.info(f"AkShare fetched {len(all_data)} records for China gold reserves")

            return {
                "type": "akshare",
                "data": all_data,
            }

        except Exception as e:
            logger.error(f"AkShare fetch failed: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        解析日期字符串

        支持格式:
        - "2024年1月份" -> "2024-01"
        - "2024-01" -> "2024-01"
        - "202401" -> "2024-01"
        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # 格式: "2024年1月份"
        if "年" in date_str and "月" in date_str:
            try:
                import re

                match = re.search(r"(\d{4})年(\d{1,2})月", date_str)
                if match:
                    year = match.group(1)
                    month = match.group(2).zfill(2)
                    return f"{year}-{month}"
            except Exception:
                pass

        # 格式: "2024-01"
        if len(date_str) == 7 and "-" in date_str:
            return date_str

        # 格式: "202401"
        if len(date_str) == 6 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}"

        return None

    def parse(self, raw_data: Any) -> List[GoldReserve]:
        """
        解析 AkShare 数据为 GoldReserve 对象列表

        Args:
            raw_data: AkShare 返回的原始数据

        Returns:
            List[GoldReserve]: 黄金储备对象列表
        """
        if not raw_data or raw_data.get("type") != "akshare":
            return []

        reserves = []
        fetch_time = datetime.now()

        for item in raw_data.get("data", []):
            try:
                # 解析日期
                report_date = date.today()
                date_str = item.get("date")
                if date_str:
                    try:
                        report_date = datetime.strptime(date_str, "%Y-%m").date()
                    except ValueError:
                        pass

                reserves.append(
                    GoldReserve(
                        country_code=item["country_code"],
                        country_name=item["country_name"],
                        amount_tonnes=float(item["amount"]),
                        percent_of_reserves=None,  # AkShare 不提供占比数据
                        report_date=report_date,
                        data_source="AkShare",
                        fetch_time=fetch_time,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse AkShare item: {e}")
                continue

        return reserves
