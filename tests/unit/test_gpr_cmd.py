"""Unit tests for gpr commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcli.commands.gpr import _compare, _history, _index


def _make_session_mock():
    session_mock = MagicMock()
    session_mock.return_value.__aenter__ = AsyncMock(return_value=None)
    session_mock.return_value.__aexit__ = AsyncMock(return_value=False)
    return session_mock


@pytest.fixture
def mock_container():
    with patch("fcli.commands.gpr.container") as mock:
        mock.session = _make_session_mock()
        mock.gpr_service = AsyncMock()
        yield mock


@pytest.fixture
def mock_presenter():
    with patch("fcli.commands.gpr.ConsolePresenter") as mock:
        yield mock


class TestIndex:
    async def test_index_basic(self, mock_container, mock_presenter):
        analysis = {"country": "WLD", "index_type": "GPR", "current": 150.0}
        history = [{"month": "2026-01", "value": 150.0}]
        mock_container.gpr_service.get_gpr_analysis.return_value = analysis
        mock_container.gpr_service.get_gpr_history.return_value = history

        await _index(update=False, full=False, chart=True, country="WLD", index_type="GPR")

        mock_container.gpr_service.get_gpr_analysis.assert_called_once_with(country_code="WLD", index_type="GPR")
        mock_presenter.print_gpr_report.assert_called_once_with(analysis)
        mock_container.gpr_service.get_gpr_history.assert_called_once_with(
            months=120, country_code="WLD", index_type="GPR"
        )
        mock_presenter.print_gpr_chart.assert_called_once()

    async def test_index_no_chart(self, mock_container, mock_presenter):
        analysis = {"country": "WLD", "index_type": "GPR", "current": 150.0}
        mock_container.gpr_service.get_gpr_analysis.return_value = analysis

        await _index(update=False, full=False, chart=False, country="WLD", index_type="GPR")

        mock_presenter.print_gpr_report.assert_called_once_with(analysis)
        mock_container.gpr_service.get_gpr_history.assert_not_called()

    async def test_index_with_update(self, mock_container, mock_presenter):
        mock_container.gpr_service.update_data.return_value = {
            "success": True,
            "records": 500,
        }
        mock_container.gpr_service.get_gpr_analysis.return_value = None

        await _index(update=True, full=False, chart=False, country="WLD", index_type="GPR")

        mock_container.gpr_service.update_data.assert_called_once_with(full=False)
        mock_presenter.print_success.assert_called_once()
        assert "500" in mock_presenter.print_success.call_args[0][0]

    async def test_index_update_failure(self, mock_container, mock_presenter):
        mock_container.gpr_service.update_data.return_value = {
            "success": False,
            "error": "Network error",
        }

        await _index(update=True, full=False, chart=False, country="WLD", index_type="GPR")

        mock_presenter.print_error.assert_called_once()
        assert "Network error" in mock_presenter.print_error.call_args[0][0]
        mock_container.gpr_service.get_gpr_analysis.assert_not_called()

    async def test_index_no_analysis_with_country_hint(self, mock_container, mock_presenter):
        mock_container.gpr_service.get_gpr_analysis.return_value = None

        await _index(update=False, full=False, chart=False, country="CHN", index_type="GPRT")

        mock_presenter.print_warning.assert_called_once()
        warning_msg = mock_presenter.print_warning.call_args[0][0]
        assert "CHN" in warning_msg

    async def test_index_no_analysis_default(self, mock_container, mock_presenter):
        mock_container.gpr_service.get_gpr_analysis.return_value = None

        await _index(update=False, full=False, chart=False, country="WLD", index_type="GPR")

        mock_presenter.print_warning.assert_called_once()
        assert "暂无 GPR 数据" in mock_presenter.print_warning.call_args[0][0]

    async def test_index_full_update(self, mock_container, mock_presenter):
        mock_container.gpr_service.update_data.return_value = {
            "success": True,
            "records": 2000,
        }
        analysis = {"country": "WLD", "index_type": "GPR", "current": 150.0}
        mock_container.gpr_service.get_gpr_analysis.return_value = analysis

        await _index(update=True, full=True, chart=False, country="WLD", index_type="GPR")

        mock_container.gpr_service.update_data.assert_called_once_with(full=True)


class TestHistory:
    async def test_history_with_data(self, mock_container, mock_presenter):
        data = [{"month": "2026-01", "value": 150.0}]
        mock_container.gpr_service.get_gpr_history.return_value = data

        await _history(months=60, country="CHN", index_type="GPR")

        mock_container.gpr_service.get_gpr_history.assert_called_once_with(
            months=60, country_code="CHN", index_type="GPR"
        )
        mock_presenter.print_gpr_chart.assert_called_once_with(data, country_code="CHN", index_type="GPR")

    async def test_history_no_data(self, mock_container, mock_presenter):
        mock_container.gpr_service.get_gpr_history.return_value = []

        await _history(months=120, country="WLD", index_type="GPR")

        mock_presenter.print_warning.assert_called_once()
        assert "暂无历史数据" in mock_presenter.print_warning.call_args[0][0]

    async def test_history_custom_params(self, mock_container, mock_presenter):
        data = [{"month": "2026-01", "value": 100.0}]
        mock_container.gpr_service.get_gpr_history.return_value = data

        await _history(months=30, country="USA", index_type="GPRT")

        mock_container.gpr_service.get_gpr_history.assert_called_once_with(
            months=30, country_code="USA", index_type="GPRT"
        )


class TestCompare:
    async def test_compare_with_data(self, mock_container, mock_presenter):
        comparison = [
            {"country": "CHN", "gpr": 100.0},
            {"country": "USA", "gpr": 120.0},
        ]
        mock_container.gpr_service.get_multi_country_comparison.return_value = comparison

        await _compare(["CHN", "USA"])

        mock_container.gpr_service.get_multi_country_comparison.assert_called_once_with(country_codes=["CHN", "USA"])
        mock_presenter.print_country_comparison.assert_called_once_with(comparison)

    async def test_compare_default_countries(self, mock_container, mock_presenter):
        comparison = [{"country": "CHN", "gpr": 100.0}]
        mock_container.gpr_service.get_multi_country_comparison.return_value = comparison

        await _compare(None)

        call_args = mock_container.gpr_service.get_multi_country_comparison.call_args
        country_codes = call_args.kwargs["country_codes"]
        assert "CHN" in country_codes
        assert "USA" in country_codes
        assert len(country_codes) == 10

    async def test_compare_no_data(self, mock_container, mock_presenter):
        mock_container.gpr_service.get_multi_country_comparison.return_value = None

        await _compare(["CHN", "USA"])

        mock_presenter.print_warning.assert_called_once()
