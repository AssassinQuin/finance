"""GPR (Geopolitical Risk Index) models."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class GPRHistory(BaseModel):
    """GPR history data model for database operations."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    country_code: str = "WLD"
    report_date: date
    gpr_index: float
    data_source: str = "Caldara-Iacoviello"
    created_at: datetime | None = None
