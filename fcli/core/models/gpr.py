"""GPR (Geopolitical Risk Index) models."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class GPRHistory(BaseModel):
    """GPR history data model for database operations."""

    id: Optional[int] = None
    country_code: str = "WLD"  # Default to World aggregate
    report_date: date
    gpr_index: float
    gpr_threat: Optional[float] = None  # GPR Threat component
    gpr_act: Optional[float] = None  # GPR Act component
    data_source: str = "Caldara-Iacoviello"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
