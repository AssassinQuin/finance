"""Unit tests for market commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcli.commands.market import _get_fund_detail, _search_funds, _update_fund_data
from fcli.core.models import FundType
from tests.unit.conftest import make_sample_fund, make_sample_fund_detail


def _make_session_mock():
    session_mock = MagicMock()
    session_mock.return_value.__aenter__ = AsyncMock(return_value=None)
    session_mock.return_value.__aexit__ = AsyncMock(return_value=False)
    return session_mock


@pytest.fixture
def mock_container():
    with patch("fcli.commands.market.container") as mock:
        mock.session = _make_session_mock()
        mock.fund_service = AsyncMock()
        yield mock


@pytest.fixture
def mock_presenter():
    with patch("fcli.commands.market.ConsolePresenter") as mock:
        yield mock


class TestSearchFunds:
    async def test_search_with_results(self, mock_container, mock_presenter):
        funds = [make_sample_fund("510300"), make_sample_fund("159919", "沪深300")]
        mock_container.fund_service.search.return_value = funds

        result = await _search_funds("沪深300", None, 20)

        assert result == funds
        mock_container.fund_service.search.assert_called_once_with("沪深300", None, 20)

    async def test_search_with_type_filter(self, mock_container, mock_presenter):
        funds = [make_sample_fund("510300")]
        mock_container.fund_service.search.return_value = funds

        result = await _search_funds("510300", FundType.ETF, 10)

        assert result == funds
        mock_container.fund_service.search.assert_called_once_with("510300", FundType.ETF, 10)

    async def test_search_no_results(self, mock_container, mock_presenter):
        mock_container.fund_service.search.return_value = []

        result = await _search_funds("不存在的基金", None, 20)

        assert result == []


class TestGetFundDetail:
    async def test_detail_found(self, mock_container, mock_presenter):
        detail = make_sample_fund_detail()
        mock_container.fund_service.get_detail.return_value = detail

        result = await _get_fund_detail("510300")

        assert result == detail
        mock_container.fund_service.get_detail.assert_called_once_with("510300")

    async def test_detail_not_found(self, mock_container, mock_presenter):
        mock_container.fund_service.get_detail.return_value = None

        result = await _get_fund_detail("000000")

        assert result is None
        mock_container.fund_service.get_detail.assert_called_once_with("000000")


class TestUpdateFundData:
    async def test_update_success(self, mock_container, mock_presenter):
        mock_container.fund_service.update_fund_data.return_value = 50

        result = await _update_fund_data(None, force=False)

        assert result == 50
        mock_container.fund_service.update_fund_data.assert_called_once_with(None, force=False)

    async def test_update_with_type(self, mock_container, mock_presenter):
        mock_container.fund_service.update_fund_data.return_value = 20

        result = await _update_fund_data("ETF", force=True)

        assert result == 20
        mock_container.fund_service.update_fund_data.assert_called_once_with("ETF", force=True)

    async def test_update_no_changes(self, mock_container, mock_presenter):
        mock_container.fund_service.update_fund_data.return_value = 0

        result = await _update_fund_data(None, force=False)

        assert result == 0
