"""Base scraper class. Provides common fetch/parse/scrape pattern for all scrapers."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from ...utils.time_util import utcnow

T = TypeVar("T")


@dataclass
class ScraperResult(Generic[T]):
    """Result from a scraper operation."""

    success: bool
    data: list[T] = field(default_factory=list)
    source: str = ""
    error_message: str | None = None
    fetch_time_ms: int = 0
    records_count: int = 0

    def __post_init__(self):
        if self.data:
            self.records_count = len(self.data)


class BaseScraper(ABC, Generic[T]):
    """
    Abstract base class for all scrapers.

    Subclasses must implement:
    - fetch(): Async method to fetch raw data
    - parse(): Method to parse raw data into domain objects
    - source_name: Property returning the source name
    """

    def __init__(self):
        self._last_fetch_time: datetime | None = None

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @abstractmethod
    async def fetch(self) -> Any:
        pass

    @abstractmethod
    def parse(self, raw_data: Any) -> list[T]:
        pass

    async def scrape(self) -> ScraperResult[T]:
        start_time = time.time()

        try:
            raw_data = await self.fetch()

            if raw_data is None:
                return ScraperResult(
                    success=False,
                    source=self.source_name,
                    error_message="No data returned from fetch",
                    fetch_time_ms=int((time.time() - start_time) * 1000),
                )

            records = self.parse(raw_data)
            self._last_fetch_time = utcnow()

            return ScraperResult(
                success=True,
                data=records,
                source=self.source_name,
                fetch_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            return ScraperResult(
                success=False,
                source=self.source_name,
                error_message=str(e),
                fetch_time_ms=int((time.time() - start_time) * 1000),
            )
