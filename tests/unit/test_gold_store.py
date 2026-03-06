"""Unit tests for GoldReserveStore."""

import pytest
from datetime import date

from fcli.core.stores.gold import GoldReserveStore
from fcli.core.models import GoldReserve


@pytest.mark.asyncio
class TestGoldReserveStore:
    """Tests for GoldReserveStore with V2 schema."""

    async def test_save_gold_reserve(self, db_setup, sample_gold_data):
        """Test saving gold reserve data."""
        result = await GoldReserveStore.save(sample_gold_data)
        assert result is True

    async def test_get_latest_gold_reserve(self, db_setup):
        """Test retrieving latest gold reserve."""
        latest = await GoldReserveStore.get_latest("USA")
        assert latest is not None
        assert latest.country_code == "USA"
        assert latest.amount_tonnes > 0

    async def test_get_latest_date(self, db_setup):
        """Test getting latest data date."""
        latest_date = await GoldReserveStore.get_latest_date()
        assert latest_date is not None
        assert isinstance(latest_date, date)

    async def test_get_latest_with_multi_period_changes(self, db_setup):
        """Test multi-period change calculation."""
        results = await GoldReserveStore.get_latest_with_multi_period_changes()
        assert isinstance(results, list)
        assert len(results) > 0

        result = results[0]
        assert "code" in result
        assert "country" in result
        assert "amount" in result
        assert "change_1m" in result
        assert "change_3m" in result
        assert "change_6m" in result
        assert "change_12m" in result

    async def test_get_country_history(self, db_setup):
        """Test retrieving country history."""
        history = await GoldReserveStore.get_country_history("USA", days=30)
        assert isinstance(history, list)
        if len(history) > 0:
            assert all(isinstance(h, GoldReserve) for h in history)
