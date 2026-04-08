"""Gold reserve and central bank models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from ...utils.time_util import MONTH_FORMAT


class GoldReserve(BaseModel):
    """Gold reserve data model for database operations."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    country_code: str = ""
    country_name: str = ""
    amount_tonnes: float = 0.0
    report_date: date | None = None
    data_source: str = ""
    fetch_time: datetime | None = None

    @classmethod
    def from_monthly(
        cls, date_str: str, tonnes: float, country_code: str, country_name: str, source: str
    ) -> GoldReserve:
        dt = datetime.strptime(date_str, MONTH_FORMAT).date()
        return cls(
            country_code=country_code,
            country_name=country_name,
            amount_tonnes=round(tonnes, 2),
            report_date=dt,
            data_source=source,
            fetch_time=datetime.now(),
        )
