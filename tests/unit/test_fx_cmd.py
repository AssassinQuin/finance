"""Unit tests for fx commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcli.commands.fx import _rate
from tests.unit.conftest import make_sample_exchange_rate


def _make_session_mock():
    session_mock = MagicMock()
    session_mock.return_value.__aenter__ = AsyncMock(return_value=None)
    session_mock.return_value.__aexit__ = AsyncMock(return_value=False)
    return session_mock


@pytest.fixture
def mock_container():
    with patch("fcli.commands.fx.container") as mock:
        mock.session = _make_session_mock()
        mock.forex_service = AsyncMock()
        yield mock


@pytest.fixture
def mock_presenter():
    with patch("fcli.commands.fx.ConsolePresenter") as mock:
        yield mock


class TestRate:
    async def test_rate_single_pair(self, mock_container, mock_presenter):
        rate = make_sample_exchange_rate("USD", "CNY", 7.25)
        mock_container.forex_service.get_rate.return_value = rate

        await _rate("USD", "CNY")

        mock_container.forex_service.get_rate.assert_called_once_with("USD", "CNY")
        mock_presenter.print_exchange_rate.assert_called_once_with(rate)

    async def test_rate_single_pair_not_found(self, mock_container, mock_presenter):
        mock_container.forex_service.get_rate.return_value = None

        await _rate("USD", "XYZ")

        mock_container.forex_service.get_rate.assert_called_once_with("USD", "XYZ")
        mock_presenter.print_error.assert_called_once()
        assert "无法获取" in mock_presenter.print_error.call_args[0][0]

    async def test_rate_all_for_base(self, mock_container, mock_presenter):
        rate1 = make_sample_exchange_rate("USD", "CNY", 7.25)
        rate2 = make_sample_exchange_rate("USD", "EUR", 0.92)
        rates_dict = {"CNY": rate1, "EUR": rate2}
        mock_container.forex_service.get_all_rates.return_value = rates_dict

        await _rate("USD", None)

        mock_container.forex_service.get_all_rates.assert_called_once_with("USD")
        mock_presenter.print_exchange_rates.assert_called_once()
        call_args = mock_presenter.print_exchange_rates.call_args
        assert call_args[0][1] == "USD"

    async def test_rate_all_for_base_empty(self, mock_container, mock_presenter):
        mock_container.forex_service.get_all_rates.return_value = {}

        await _rate("XYZ", None)

        mock_container.forex_service.get_all_rates.assert_called_once_with("XYZ")
        mock_presenter.print_error.assert_called_once()
        assert "无法获取" in mock_presenter.print_error.call_args[0][0]
