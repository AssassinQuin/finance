"""Unit tests for gold commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcli.commands.gold import _reserves, _supply


def _make_session_mock():
    session_mock = MagicMock()
    session_mock.return_value.__aenter__ = AsyncMock(return_value=None)
    session_mock.return_value.__aexit__ = AsyncMock(return_value=False)
    return session_mock


@pytest.fixture
def mock_container():
    with patch("fcli.commands.gold.container") as mock:
        mock.session = _make_session_mock()
        mock.gold_reserve_service = AsyncMock()
        mock.gold_supply_demand_service = AsyncMock()
        yield mock


@pytest.fixture
def mock_presenter():
    with patch("fcli.commands.gold.ConsolePresenter") as mock:
        yield mock


class TestReserves:
    async def test_reserves_with_data(self, mock_container, mock_presenter):
        reserves_data = [{"code": "USA", "country": "United States", "amount": 8133.5}]
        balance_data = {"total_demand": 1000.0, "total_supply": 900.0}
        mock_container.gold_reserve_service.fetch_all_with_auto_update.return_value = reserves_data
        mock_container.gold_supply_demand_service.fetch_global_supply_demand.return_value = balance_data

        await _reserves(update=False)

        mock_container.gold_reserve_service.fetch_all_with_auto_update.assert_called_once_with(force=False)
        mock_container.gold_supply_demand_service.fetch_global_supply_demand.assert_called_once()
        mock_presenter.print_gold_report.assert_called_once()
        report_arg = mock_presenter.print_gold_report.call_args[0][0]
        assert report_arg["reserves"] == reserves_data
        assert report_arg["balance"] == balance_data

    async def test_reserves_force_update(self, mock_container, mock_presenter):
        mock_container.gold_reserve_service.fetch_all_with_auto_update.return_value = [
            {"code": "USA", "country": "United States", "amount": 8133.5}
        ]
        mock_container.gold_supply_demand_service.fetch_global_supply_demand.return_value = None

        await _reserves(update=True)

        mock_container.gold_reserve_service.fetch_all_with_auto_update.assert_called_once_with(force=True)

    async def test_reserves_no_data(self, mock_container, mock_presenter):
        mock_container.gold_reserve_service.fetch_all_with_auto_update.return_value = []

        await _reserves(update=False)

        mock_presenter.print_warning.assert_called_once()
        assert "无法获取黄金储备数据" in mock_presenter.print_warning.call_args[0][0]
        mock_presenter.print_gold_report.assert_not_called()


class TestSupply:
    async def test_supply_with_data(self, mock_container, mock_presenter):
        balance_data = {"total_demand": 1000.0, "total_supply": 900.0}
        mock_container.gold_supply_demand_service.fetch_global_supply_demand.return_value = balance_data

        await _supply()

        mock_container.gold_supply_demand_service.fetch_global_supply_demand.assert_called_once()
        mock_presenter.print_gold_supply_balance.assert_called_once_with(balance_data)

    async def test_supply_no_data(self, mock_container, mock_presenter):
        mock_container.gold_supply_demand_service.fetch_global_supply_demand.return_value = None

        await _supply()

        mock_presenter.print_warning.assert_called_once()
        assert "无法获取黄金供需数据" in mock_presenter.print_warning.call_args[0][0]
        mock_presenter.print_gold_supply_balance.assert_not_called()
