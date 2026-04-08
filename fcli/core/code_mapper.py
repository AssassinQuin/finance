"""统一代码映射模块

所有 code↔api_code / secid 转换的唯一入口。
不再在 DataSource 配置类或 QuoteSource 中散布映射逻辑。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Asset
    from .models.base import AssetType, Market


class CodeMapper:
    """统一代码映射 — code→api_code / secid 的唯一真相来源"""

    def infer_market(self, code: str) -> Market:
        from .models.base import Market

        code_upper = code.upper().strip()

        if code_upper.startswith("HK") or (code.isdigit() and len(code) == 5):
            return Market.HK

        if code_upper.startswith(("SH", "SZ")) or (code.isdigit() and len(code) == 6):
            return Market.CN

        if code.isalpha():
            return Market.US

        return Market.US

    def infer_type(self, code: str) -> AssetType:
        from .models.base import AssetType

        gold_codes = {"GC", "XAU", "GOLD"}
        if code.upper().strip() in gold_codes:
            return AssetType.GOLD

        if code.isdigit() and len(code) == 6:
            prefix2 = code[:2]
            prefix3 = code[:3]
            fund_prefixes_2 = {"11", "15", "16", "50", "51", "52"}
            fund_prefixes_3 = {"159"}
            if prefix2 in fund_prefixes_2 or prefix3 in fund_prefixes_3:
                return AssetType.FUND

        return AssetType.STOCK

    def to_sina_code(self, code: str, market: Market) -> str:
        from .models.base import Market

        if market == Market.CN:
            if code[:2] in ("sh", "SH", "sz", "SZ"):
                return code.lower()
            if code[0] in ("5", "6", "9"):
                return f"sh{code}"
            return f"sz{code}"
        if market == Market.HK:
            return f"rt_hk{code}"
        if market == Market.US:
            return f"gb_{code.lower()}"
        raise ValueError(f"Sina: unsupported market {market}")

    def to_eastmoney_secid(self, api_code: str, market: Market) -> str:
        from .models.base import Market

        if market == Market.CN:
            if api_code[:2] in ("sh", "SH", "sz", "SZ"):
                code = api_code[2:]
            else:
                code = api_code
            mc = 1 if code[0] in ("5", "6", "9") else 0
            return f"{mc}.{code}"
        if market == Market.HK:
            code = api_code.replace("rt_hk", "")
            return f"116.{code}"
        if market == Market.US:
            return f"105.{api_code}"
        if market == Market.GLOBAL:
            code = api_code.split(".")[1] if "." in api_code else api_code
            return f"100.{code}"
        raise ValueError(f"Eastmoney: unsupported market {market}")

    def create_asset(self, code: str) -> Asset:
        from .models import Asset

        code = code.strip()
        code_upper = code.upper()
        market = self.infer_market(code)
        asset_type = self.infer_type(code)
        api_code = self.to_sina_code(code, market)
        return Asset(
            code=code_upper,
            api_code=api_code,
            name=code_upper,
            market=market,
            type=asset_type,
        )


code_mapper = CodeMapper()
