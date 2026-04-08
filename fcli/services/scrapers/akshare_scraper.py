"""
AkShare 数据源爬虫 - 中国黄金储备历史数据
数据来源: 中国人民银行 / 国家外汇管理局 (via AkShare)
"""

import re
from typing import Any

from ...core.models import GoldReserve
from ...core.models.base import COUNTRY_CN_CODE, COUNTRY_CN_NAME, SOURCE_PBOC
from ...utils.logger import get_logger
from .base import BaseScraper

logger = get_logger("fcli.scraper.akshare")


class AkShareScraper(BaseScraper):
    """
    AkShare 数据源爬虫

    使用 macro_china_foreign_exchange_gold() 获取中国官方黄金储备数据（万盎司）
    数据来源: 中国人民银行 / 国家外汇管理局
    """

    def __init__(self):
        super().__init__()
        self._source_name = SOURCE_PBOC

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
        except ImportError:
            logger.error("AkShare 未安装，请运行: pip install akshare")
            return None

        try:
            logger.info("Fetching China gold reserves from AkShare (PBOC)...")

            df = ak.macro_china_foreign_exchange_gold()

            if df is None or df.empty:
                logger.warning("AkShare returned empty data")
                return None

            all_data = []
            for _, row in df.iterrows():
                try:
                    date_str = str(row.iloc[0]).strip()
                    gold_wan_oz = row.iloc[1]

                    if gold_wan_oz is None:
                        continue
                    gold_val = float(gold_wan_oz)
                    if gold_val <= 0:
                        continue

                    parsed_date = self._parse_date(date_str)
                    if not parsed_date:
                        continue

                    from ...core.config import config

                    amount_tonnes = gold_val * config.gold.wan_oz_to_tonne
                    all_data.append(
                        {
                            "country_code": COUNTRY_CN_CODE,
                            "country_name": COUNTRY_CN_NAME,
                            "amount": round(amount_tonnes, 2),
                            "date": parsed_date,
                        }
                    )
                except Exception as e:
                    logger.debug("Failed to parse row: %s", e)
                    continue

            if not all_data:
                logger.warning("No valid data parsed from AkShare")
                return None

            all_data.sort(key=lambda x: x["date"], reverse=True)

            logger.info("AkShare fetched %d records for China gold reserves", len(all_data))

            return {
                "type": "akshare",
                "data": all_data,
            }

        except Exception as e:
            logger.error("AkShare fetch failed: %s", e)
            return None

    def _parse_date(self, date_str: str) -> str | None:
        """
        解析日期字符串

        支持格式:
        - "2026.2" or "2026.02" -> "2026-02"
        - "2024年1月份" -> "2024-01"
        - "2024-01" -> "2024-01"
        - "202401" -> "2024-01"
        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        if "年" in date_str and "月" in date_str:
            match = re.search(r"(\d{4})年(\d{1,2})月", date_str)
            if match:
                year = match.group(1)
                month = match.group(2).zfill(2)
                return f"{year}-{month}"

        if "." in date_str and "年" not in date_str:
            match = re.match(r"(\d{4})\.(\d{1,2})", date_str)
            if match:
                year = match.group(1)
                month = match.group(2).zfill(2)
                return f"{year}-{month}"

        if len(date_str) == 7 and "-" in date_str:
            return date_str

        if len(date_str) == 6 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}"

        return None

    def parse(self, raw_data: Any) -> list[GoldReserve]:
        if not raw_data or raw_data.get("type") != "akshare":
            return []

        reserves = []

        for item in raw_data.get("data", []):
            try:
                reserves.append(
                    GoldReserve.from_monthly(
                        date_str=item["date"],
                        tonnes=float(item["amount"]),
                        country_code=item["country_code"],
                        country_name=item["country_name"],
                        source=SOURCE_PBOC,
                    )
                )
            except Exception as e:
                logger.warning("Failed to parse AkShare item: %s", e)
                continue

        return reserves

    async def get_china_latest(self) -> GoldReserve | None:
        raw = await self.fetch()
        if not raw or not raw.get("data"):
            return None

        latest = raw["data"][0]
        return GoldReserve.from_monthly(
            date_str=latest["date"],
            tonnes=float(latest["amount"]),
            country_code=COUNTRY_CN_CODE,
            country_name=COUNTRY_CN_NAME,
            source=SOURCE_PBOC,
        )

    async def get_china_history(self) -> list[GoldReserve]:
        """Fetch China gold reserve history from PBOC via AkShare.

        Returns:
            List of GoldReserve objects sorted by date ascending.
        """
        raw = await self.fetch()
        reserves = self.parse(raw)
        reserves.sort(key=lambda r: r.report_date)
        return reserves
