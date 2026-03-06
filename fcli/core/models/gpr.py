"""GPR (Geopolitical Risk Index) models."""

from datetime import date, datetime

from pydantic import BaseModel


class GPRHistory(BaseModel):
    """GPR history data model for database operations."""

    id: int | None = None
    country_code: str = "WLD"
    report_date: date
    gpr_index: float
    data_source: str = "Caldara-Iacoviello"
    created_at: datetime | None = None

    class Config:
        from_attributes = True
