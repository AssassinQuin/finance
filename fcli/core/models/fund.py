"""Fund market data models."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .base import Market


class FundType(str, Enum):
    """Fund type enumeration."""

    INDEX = "INDEX"
    ETF = "ETF"
    FUND = "FUND"


class InvestType(str, Enum):
    """Investment type enumeration."""

    PASSIVE = "被动指数型"
    ENHANCED = "增强指数型"
    ACTIVE = "主动管理型"


class Fund(BaseModel):
    """Fund basic information with optional latest scale."""

    code: str = Field(..., description="Fund code (基金代码)")
    name: str = Field(..., description="Full fund name (基金全称)")
    name_short: str | None = Field(None, description="Short name (基金简称)")
    fund_type: FundType = Field(..., description="Fund type: INDEX, ETF, FUND")
    market: Market = Field(default=Market.CN, description="Market: CN, HK, US")
    invest_type: InvestType | None = Field(None, description="Investment type")

    management_fee: float | None = Field(None, description="Annual management fee rate")
    custody_fee: float | None = Field(None, description="Annual custody fee rate")

    fund_company: str | None = Field(None, description="Fund company")
    tracking_index: str | None = Field(None, description="Tracking index")
    inception_date: date | None = Field(None, description="Inception date")
    listing_date: date | None = Field(None, description="Listing date (for ETFs)")

    scale: float | None = Field(None, description="Current scale in 100M yuan (规模-亿元)")
    share: float | None = Field(None, description="Shares in 100M (份额-亿份)")
    nav: float | None = Field(None, description="Net asset value (单位净值)")
    scale_date: date | None = Field(None, description="Scale data date")

    is_active: bool = Field(default=True, description="Is fund active")
    extra: dict[str, Any] = Field(default_factory=dict)


class FundScale(BaseModel):
    """Fund scale snapshot."""

    fund_code: str = Field(..., description="Fund code")
    report_date: date = Field(..., description="Report date")
    scale: float | None = Field(None, description="Scale in 100M yuan")
    share: float | None = Field(None, description="Shares in 100M")
    nav: float | None = Field(None, description="Net asset value")
    fetched_at: datetime | None = Field(None, description="Fetch timestamp")


class FundSearchResult(BaseModel):
    """Fund search result with relevance score."""

    fund: Fund
    relevance: float = Field(..., description="Search relevance score (0-1)")
    matched_field: str = Field(..., description="Which field matched: code, name, name_short")


class FundDetail(Fund):
    """Extended fund detail with scale history."""

    scale_history: list[FundScale] = Field(default_factory=list, description="Recent scale history")

    @classmethod
    def from_fund(cls, fund: Fund, scale_history: list[FundScale] | None = None) -> "FundDetail":
        return cls(**fund.model_dump(), scale_history=scale_history or [])
