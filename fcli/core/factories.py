"""Asset factory for unified asset creation."""

from .config import symbol_registry
from .models import Asset, Market


class AssetFactory:
    """Unified factory for creating Asset objects"""

    @staticmethod
    def from_code(code: str) -> Asset:
        code = code.strip()
        code_upper = code.upper()
        market = symbol_registry.infer_market(code)
        asset_type = symbol_registry.infer_type(code)
        api_code = AssetFactory._to_api_code(code, market)
        return Asset(
            code=code_upper,
            api_code=api_code,
            name=code_upper,
            market=market,
            type=asset_type,
        )

    @staticmethod
    def _to_api_code(code: str, market: Market) -> str:
        code_lower = code.lower()
        if market == Market.CN:
            if code_lower.startswith(("sh", "sz")):
                return code_lower
            prefix = code[:2]
            return f"sh{code}" if prefix in ("60", "68") else f"sz{code}"
        elif market == Market.HK:
            code_num = code[-5:] if code.upper().startswith("HK") else code
            return f"rt_hk{code_num}"
        else:
            return code_lower
