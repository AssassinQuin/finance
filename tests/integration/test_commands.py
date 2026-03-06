"""Integration tests for CLI commands."""

import pytest
from click.testing import CliRunner

from fcli.main import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


class TestGoldCommand:
    """Integration tests for gold command."""

    def test_gold_command_success(self, runner):
        """Test gold command executes successfully."""
        result = runner.invoke(app, ["gold"])
        assert result.exit_code == 0
        assert "央行黄金储备" in result.output or "Central Bank Gold Reserves" in result.output

    def test_gold_command_with_update(self, runner):
        """Test gold command with update flag."""
        result = runner.invoke(app, ["gold", "-u"])
        assert result.exit_code == 0


class TestGPRCommand:
    """Integration tests for gpr command."""

    def test_gpr_command_success(self, runner):
        """Test gpr command executes successfully."""
        result = runner.invoke(app, ["gpr"])
        assert result.exit_code == 0
        assert "GPR" in result.output or "地缘风险" in result.output


class TestFXCommand:
    """Integration tests for fx command."""

    def test_fx_command_default(self, runner):
        """Test fx command with default parameters."""
        result = runner.invoke(app, ["fx"])
        assert result.exit_code == 0
        assert "USD" in result.output or "汇率" in result.output

    def test_fx_command_specific_pair(self, runner):
        """Test fx command with specific currency pair."""
        result = runner.invoke(app, ["fx", "USD", "CNY"])
        assert result.exit_code == 0


class TestWatchlistCommand:
    """Integration tests for watchlist commands."""

    def test_watchlist_list(self, runner):
        """Test watchlist list command."""
        result = runner.invoke(app, ["watchlist"])
        assert result.exit_code == 0

    def test_watchlist_ls_alias(self, runner):
        """Test watchlist ls alias."""
        result = runner.invoke(app, ["ls"])
        assert result.exit_code == 0
