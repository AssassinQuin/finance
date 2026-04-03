"""Unit test fixtures for command tests."""

from contextlib import asynccontextmanager
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcli.core.models import (
    Asset,
    AssetType,
    ExchangeRate,
    Fund,
    FundDetail,
    FundScale,
    FundType,
    Market,
    Quote,
)


@pytest.fixture
def mock_presenter():
    """Mock ConsolePresenter for all command tests."""
    with (
        patch("fcli.commands.watchlist.ConsolePresenter") as wl_p,
        patch("fcli.commands.fx.ConsolePresenter") as fx_p,
        patch("fcli.commands.gold.ConsolePresenter") as gold_p,
        patch("fcli.commands.gpr.ConsolePresenter") as gpr_p,
        patch("fcli.commands.market.ConsolePresenter") as mk_p,
    ):
        yield {
            "watchlist": wl_p,
            "fx": fx_p,
            "gold": gold_p,
            "gpr": gpr_p,
            "market": mk_p,
        }


def make_sample_asset(code: str = "600519", name: str = "贵州茅台") -> Asset:
    return Asset(
        code=code,
        api_code=f"sh{code}",
        name=name,
        market=Market.CN,
        type=AssetType.STOCK,
    )


def make_sample_quote(code: str = "600519", name: str = "贵州茅台") -> Quote:
    return Quote(
        code=code,
        name=name,
        price=1800.0,
        change_percent=1.5,
        update_time=datetime.now(),
        market=Market.CN,
        type=AssetType.STOCK,
    )


def make_sample_exchange_rate(base: str = "USD", quote: str = "CNY", rate: float = 7.25) -> ExchangeRate:
    return ExchangeRate(
        base_currency=base,
        quote_currency=quote,
        rate=rate,
        source="test",
        update_time=datetime.now(),
    )


def make_sample_fund(code: str = "510300", name: str = "沪深300ETF") -> Fund:
    return Fund(
        code=code,
        name=name,
        name_short=name,
        fund_type=FundType.ETF,
        market=Market.CN,
    )


def make_sample_fund_detail(code: str = "510300", name: str = "沪深300ETF") -> FundDetail:
    fund = make_sample_fund(code, name)
    return FundDetail.from_fund(
        fund,
        scale_history=[
            FundScale(
                fund_code=code,
                report_date=date(2026, 1, 1),
                scale=100.0,
            )
        ],
    )
