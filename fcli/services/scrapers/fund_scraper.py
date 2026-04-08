"""Fund scraper using AKShare."""

import asyncio
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ...core.models import Fund, FundType, InvestType
from ...utils.logger import get_logger
from ...utils.time_util import DATE_FORMAT
from .base import BaseScraper, ScraperResult

logger = get_logger("fcli.scraper.fund")

US_INDEX_FUND_SPECS = [
    {
        "code": ".INX",
        "name": "S&P 500 Index",
        "name_short": "标普500",
        "fund_type": FundType.INDEX,
        "market": "US",
        "is_active": True,
    },
    {
        "code": ".DJI",
        "name": "Dow Jones Industrial Average",
        "name_short": "道琼斯工业平均指数",
        "fund_type": FundType.INDEX,
        "market": "US",
        "is_active": True,
    },
    {
        "code": ".IXIC",
        "name": "Nasdaq Composite Index",
        "name_short": "纳斯达克综合指数",
        "fund_type": FundType.INDEX,
        "market": "US",
        "is_active": True,
    },
    {
        "code": ".NDX",
        "name": "Nasdaq 100 Index",
        "name_short": "纳斯达克100指数",
        "fund_type": FundType.INDEX,
        "market": "US",
        "is_active": True,
    },
    {
        "code": "QQQ",
        "name": "Invesco QQQ Trust",
        "name_short": "纳斯达克100 ETF",
        "fund_type": FundType.ETF,
        "market": "US",
        "management_fee": 0.0020,
        "is_active": True,
    },
    {
        "code": "QQQM",
        "name": "Invesco NASDAQ 100 ETF",
        "name_short": "纳斯达克100 ETF (迷你)",
        "fund_type": FundType.ETF,
        "market": "US",
        "management_fee": 0.0015,
        "is_active": True,
    },
    {
        "code": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "name_short": "标普500 ETF",
        "fund_type": FundType.ETF,
        "market": "US",
        "management_fee": 0.0009,
        "is_active": True,
    },
    {
        "code": "IVV",
        "name": "iShares Core S&P 500 ETF",
        "name_short": "标普500 ETF (iShares)",
        "fund_type": FundType.ETF,
        "market": "US",
        "management_fee": 0.0003,
        "is_active": True,
    },
    {
        "code": "VOO",
        "name": "Vanguard S&P 500 ETF",
        "name_short": "标普500 ETF (Vanguard)",
        "fund_type": FundType.ETF,
        "market": "US",
        "management_fee": 0.0003,
        "is_active": True,
    },
    {
        "code": "DIA",
        "name": "SPDR Dow Jones Industrial Average ETF Trust",
        "name_short": "道琼斯ETF",
        "fund_type": FundType.ETF,
        "market": "US",
        "management_fee": 0.0016,
        "is_active": True,
    },
]


class FundScraper(BaseScraper[Fund]):
    """Scraper for fund data using AKShare."""

    def __init__(self):
        super().__init__()

    @property
    def source_name(self) -> str:
        return "AKShare"

    async def fetch(self) -> Any:
        return await self.scrape_funds(None)

    def parse(self, raw_data: Any) -> list[Fund]:
        if isinstance(raw_data, ScraperResult) and raw_data.success:
            return raw_data.data
        return []

    async def scrape_funds(self, fund_type: FundType | None = None) -> ScraperResult[Fund]:
        """Scrape funds by type."""
        try:
            if fund_type == FundType.INDEX:
                return await self._scrape_index_funds()
            elif fund_type == FundType.ETF:
                return await self._scrape_etf_funds()
            elif fund_type == FundType.FUND:
                return await self._scrape_off_exchange_funds()
            else:
                all_funds: list[Fund] = []

                result = await self._scrape_index_funds()
                if result.success and result.data:
                    all_funds.extend(result.data)

                result = await self._scrape_etf_funds()
                if result.success and result.data:
                    all_funds.extend(result.data)

                result = await self._scrape_off_exchange_funds()
                if result.success and result.data:
                    all_funds.extend(result.data)

                return ScraperResult(success=True, data=all_funds, source="AKShare")
        except Exception as e:
            logger.error(f"Failed to scrape funds: {e}")
            return ScraperResult(success=False, source="AKShare", error_message=str(e))

    async def _scrape_index_funds(self) -> ScraperResult[Fund]:
        """Scrape index funds from AKShare."""
        try:
            import akshare as ak

            df = await asyncio.to_thread(ak.fund_info_index_em)

            funds = []
            for _, row in df.iterrows():
                try:
                    fund = Fund(
                        code=str(row.get("基金代码", "")),
                        name=str(row.get("基金名称", "")),
                        fund_type=FundType.INDEX,
                        market="CN",
                        invest_type=self._parse_invest_type(row.get("跟踪方式")),
                        tracking_index=str(row.get("跟踪标的", "")) or None,
                        management_fee=self._parse_fee(row.get("手续费")),
                        is_active=True,
                    )
                    funds.append(fund)
                except Exception as e:
                    logger.warning(f"Failed to parse index fund row: {e}")
                    continue

            return ScraperResult(success=True, data=funds, source="AKShare-Index")
        except Exception as e:
            logger.error(f"Failed to scrape index funds: {e}")
            return ScraperResult(success=False, source="AKShare-Index", error_message=str(e))

    async def _scrape_etf_funds(self) -> ScraperResult[Fund]:
        """Scrape ETF funds from AKShare."""
        try:
            import akshare as ak

            df = await asyncio.to_thread(ak.fund_etf_spot_em)

            funds = []
            for _, row in df.iterrows():
                try:
                    fund = Fund(
                        code=str(row.get("代码", "")),
                        name=str(row.get("名称", "")),
                        fund_type=FundType.ETF,
                        market="CN",
                        is_active=True,
                    )
                    funds.append(fund)
                except Exception as e:
                    logger.warning(f"Failed to parse ETF row: {e}")
                    continue

            return ScraperResult(success=True, data=funds, source="AKShare-ETF")
        except Exception as e:
            logger.error(f"Failed to scrape ETF funds: {e}")
            return ScraperResult(success=False, source="AKShare-ETF", error_message=str(e))

    async def _scrape_off_exchange_funds(self) -> ScraperResult[Fund]:
        """Scrape off-exchange funds from AKShare."""
        try:
            import akshare as ak

            df = await asyncio.to_thread(ak.fund_name_em)

            funds = []
            for _, row in df.iterrows():
                try:
                    fund = Fund(
                        code=str(row.get("基金代码", "")),
                        name=str(row.get("基金简称", "")),
                        fund_type=FundType.FUND,
                        market="CN",
                        is_active=True,
                    )
                    funds.append(fund)
                except Exception as e:
                    logger.warning(f"Failed to parse fund row: {e}")
                    continue

            return ScraperResult(success=True, data=funds, source="AKShare-OffExchange")
        except Exception as e:
            logger.error(f"Failed to scrape off-exchange funds: {e}")
            return ScraperResult(success=False, source="AKShare-OffExchange", error_message=str(e))

    async def scrape_fund_detail(self, code: str) -> dict[str, Any] | None:
        """Scrape fund detail from AKShare."""
        try:
            import akshare as ak

            info = await asyncio.to_thread(ak.fund_individual_basic_info_xq, symbol=code)

            if info is None or not isinstance(info, dict):
                return None

            return {
                "scale": self._parse_scale(info.get("基金规模")),
                "fund_company": info.get("基金公司"),
                "inception_date": self._parse_date(info.get("成立时间")),
            }
        except Exception as e:
            logger.warning(f"Failed to scrape fund detail for {code}: {e}")
            return None

    async def scrape_us_indices(self) -> list[Fund]:
        """Scrape US market indices and popular ETFs."""
        return [Fund(**spec) for spec in US_INDEX_FUND_SPECS]

    def _parse_invest_type(self, value: Any) -> InvestType | None:
        """Parse invest type from string."""
        if not value:
            return None

        value_str = str(value).strip()
        if "被动" in value_str or "指数" in value_str:
            return InvestType.PASSIVE
        elif "增强" in value_str:
            return InvestType.ENHANCED
        elif "主动" in value_str:
            return InvestType.ACTIVE
        return None

    def _parse_fee(self, value: Any) -> Decimal | None:
        """Parse fee percentage from string."""
        if not value:
            return None

        try:
            value_str = str(value).replace("%", "").strip()
            return Decimal(value_str)
        except (ValueError, InvalidOperation):
            return None

    def _parse_scale(self, value: Any) -> Decimal | None:
        """Parse fund scale from string."""
        if not value:
            return None

        try:
            value_str = str(value).replace("亿元", "").strip()
            return Decimal(value_str)
        except (ValueError, InvalidOperation):
            return None

    def _parse_date(self, value: Any) -> date | None:
        """Parse date from string."""
        if not value:
            return None

        try:
            value_str = str(value).strip()
            return datetime.strptime(value_str, DATE_FORMAT).date()
        except (ValueError, TypeError):
            return None
