"""Gold reserve and central bank models."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
