"""Unit tests for GPRHistoryStore."""

import pytest

from fcli.core.models import GPRHistory
from fcli.core.stores.gpr import GPRHistoryStore


@pytest.mark.asyncio
class TestGPRHistoryStore:
    """Tests for GPRHistoryStore with V2 schema."""

    async def test_save_batch_gpr(self, db_setup, sample_gpr_data):
        """Test batch saving GPR data."""
        records = [sample_gpr_data]
        count = await GPRHistoryStore.save_batch(records)
        assert count == 1

    async def test_get_latest_gpr(self, db_setup):
        """Test retrieving latest GPR."""
        latest = await GPRHistoryStore.get_latest("WLD")
        assert latest is not None
        assert latest.country_code == "WLD"
        assert latest.gpr_index >= 0

    async def test_get_gpr_history(self, db_setup):
        """Test retrieving GPR history."""
        history = await GPRHistoryStore.get_history("WLD", months=12)
        assert isinstance(history, list)
        if len(history) > 0:
            assert all(isinstance(h, GPRHistory) for h in history)
            assert all(h.country_code == "WLD" for h in history)
