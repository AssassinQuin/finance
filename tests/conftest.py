"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from fcli.core.config import Settings
from fcli.core.database import Database


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_setup() -> AsyncGenerator:
    """Setup database connection for tests."""
    settings = Settings()
    await Database.init(settings)
    yield
    await Database.close()


@pytest.fixture
def sample_gold_data():
    """Sample gold reserve data for testing."""
    from datetime import date
    from fcli.core.models import GoldReserve

    return GoldReserve(
        country_code="USA",
        country_name="United States",
        amount_tonnes=8133.5,
        report_date=date(2026, 1, 1),
        data_source="IMF",
    )


@pytest.fixture
def sample_gpr_data():
    """Sample GPR data for testing."""
    from datetime import date
    from fcli.core.models import GPRHistory

    return GPRHistory(
        country_code="WLD",
        report_date=date(2026, 1, 1),
        gpr_index=0.05,
        data_source="Caldara-Iacoviello",
    )
