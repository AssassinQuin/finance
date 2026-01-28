from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Market(str, Enum):
    CN = "CN"     # A-share
    HK = "HK"     # Hong Kong
    US = "US"     # US Stocks
    FUND = "FUND" # China Funds
    GLOBAL = "GLOBAL" # Global Indices/Forex
    FOREX = "FOREX"
    BOND = "BOND"

class AssetType(str, Enum):
    STOCK = "STOCK"
    FUND = "FUND"
    INDEX = "INDEX"
    FOREX = "FOREX"
    BOND = "BOND"

class Asset(BaseModel):
    code: str = Field(..., description="User facing code, e.g., SP500, 000218")
    api_code: str = Field(..., description="API parameter, e.g., gb_$spx")
    name: str
    market: Market
    type: AssetType
    added_at: datetime = Field(default_factory=datetime.now)
    extra: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Quote(BaseModel):
    code: str
    name: str
    price: float
    change_percent: float
    update_time: str
    market: Market
    type: AssetType
    currency: Optional[str] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
