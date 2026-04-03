"""Unit tests for watchlist commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcli.commands.watchlist import _add, _clear, _ls, _query, _rm
from tests.unit.conftest import make_sample_asset, make_sample_quote


def _make_session_mock():
    session_mock = MagicMock()
    session_mock.return_value.__aenter__ = AsyncMock(return_value=None)
    session_mock.return_value.__aexit__ = AsyncMock(return_value=False)
    return session_mock


@pytest.fixture
def mock_container():
    with patch("fcli.commands.watchlist.container") as mock:
        mock.session = _make_session_mock()
        mock.watchlist_service = AsyncMock()
        mock.quote_service = AsyncMock()
        yield mock


@pytest.fixture
def mock_presenter():
    with patch("fcli.commands.watchlist.ConsolePresenter") as mock:
        yield mock


class TestQuery:
    async def test_query_with_assets(self, mock_container, mock_presenter):
        asset1 = make_sample_asset("600519")
        asset2 = make_sample_asset("000858", "五粮液")
        quote1 = make_sample_quote("600519")
        quote2 = make_sample_quote("000858", "五粮液")

        mock_container.watchlist_service.list_assets.return_value = [asset1, asset2]
        mock_container.quote_service.fetch_all.return_value = [quote1, quote2]

        await _query()

        mock_container.watchlist_service.list_assets.assert_called_once()
        mock_container.quote_service.fetch_all.assert_called_once_with([asset1, asset2])
        mock_presenter.print_quote_table.assert_called_once_with([quote1, quote2])

    async def test_query_empty_watchlist(self, mock_container, mock_presenter):
        mock_container.watchlist_service.list_assets.return_value = []

        await _query()

        mock_container.watchlist_service.list_assets.assert_called_once()
        mock_presenter.print_warning.assert_called_once()
        assert "自选股列表为空" in mock_presenter.print_warning.call_args[0][0]
        mock_presenter.print_quote_table.assert_not_called()


class TestAdd:
    async def test_add_assets(self, mock_container, mock_presenter):
        mock_container.watchlist_service.add_assets.return_value = 3

        result = await _add(["600519", "000858", "AAPL"])

        assert result == 3
        mock_container.watchlist_service.add_assets.assert_called_once_with(["600519", "000858", "AAPL"])

    async def test_add_single_asset(self, mock_container, mock_presenter):
        mock_container.watchlist_service.add_assets.return_value = 1

        result = await _add(["600519"])

        assert result == 1
        mock_container.watchlist_service.add_assets.assert_called_once_with(["600519"])


class TestRm:
    async def test_remove_assets(self, mock_container, mock_presenter):
        mock_container.watchlist_service.remove_assets.return_value = 2

        result = await _rm(["600519", "000858"])

        assert result == 2
        mock_container.watchlist_service.remove_assets.assert_called_once_with(["600519", "000858"])

    async def test_remove_nonexistent(self, mock_container, mock_presenter):
        mock_container.watchlist_service.remove_assets.return_value = 0

        result = await _rm(["NOTEXIST"])

        assert result == 0


class TestLs:
    async def test_ls_with_assets(self, mock_container, mock_presenter):
        assets = [make_sample_asset("600519"), make_sample_asset("000858", "五粮液")]
        mock_container.watchlist_service.list_assets.return_value = assets

        await _ls()

        mock_container.watchlist_service.list_assets.assert_called_once()
        mock_presenter.print_asset_table.assert_called_once_with(assets)

    async def test_ls_empty(self, mock_container, mock_presenter):
        mock_container.watchlist_service.list_assets.return_value = []

        await _ls()

        mock_container.watchlist_service.list_assets.assert_called_once()
        mock_presenter.print_asset_table.assert_called_once_with([])


class TestClear:
    async def test_clear_with_assets(self, mock_container, mock_presenter):
        mock_container.watchlist_service.clear_all.return_value = 5

        result = await _clear()

        assert result == 5
        mock_container.watchlist_service.clear_all.assert_called_once()

    async def test_clear_empty(self, mock_container, mock_presenter):
        mock_container.watchlist_service.clear_all.return_value = 0

        result = await _clear()

        assert result == 0
