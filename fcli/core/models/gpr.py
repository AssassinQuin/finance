"""GPR (Geopolitical Risk Index) models."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class GPRIndexType(str, Enum):
    GPR = "GPR"
    GPRT = "GPRT"
    GPRA = "GPRA"
    GPRH = "GPRH"

    @property
    def display_name(self) -> str:
        names = {
            "GPR": "GPR 总指数",
            "GPRT": "GPR 威胁指数",
            "GPRA": "GPR 行为指数",
            "GPRH": "GPR 历史指数",
        }
        return names.get(self.value, self.value)


GPR_COUNTRY_NAMES: dict[str, str] = {
    "ARG": "阿根廷",
    "AUS": "澳大利亚",
    "BEL": "比利时",
    "BRA": "巴西",
    "CAN": "加拿大",
    "CHE": "瑞士",
    "CHL": "智利",
    "CHN": "中国",
    "COL": "哥伦比亚",
    "DEU": "德国",
    "DNK": "丹麦",
    "EGY": "埃及",
    "ESP": "西班牙",
    "FIN": "芬兰",
    "FRA": "法国",
    "GBR": "英国",
    "HKG": "香港",
    "HUN": "匈牙利",
    "IDN": "印尼",
    "IND": "印度",
    "ISR": "以色列",
    "ITA": "意大利",
    "JPN": "日本",
    "KOR": "韩国",
    "MEX": "墨西哥",
    "MYS": "马来西亚",
    "NLD": "荷兰",
    "NOR": "挪威",
    "PER": "秘鲁",
    "PHL": "菲律宾",
    "POL": "波兰",
    "PRT": "葡萄牙",
    "RUS": "俄罗斯",
    "SAU": "沙特",
    "SWE": "瑞典",
    "THA": "泰国",
    "TUN": "突尼斯",
    "TUR": "土耳其",
    "TWN": "台湾",
    "UKR": "乌克兰",
    "USA": "美国",
    "VEN": "委内瑞拉",
    "VNM": "越南",
    "ZAF": "南非",
    "WLD": "全球",
}


class GPRHistory(BaseModel):
    """GPR history data model for database operations."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    country_code: str = "WLD"
    report_date: date
    gpr_index: float
    index_type: str = "GPR"
    data_source: str = "Caldara-Iacoviello"
    created_at: datetime | None = None

    @property
    def country_name(self) -> str:
        return GPR_COUNTRY_NAMES.get(self.country_code, self.country_code)
