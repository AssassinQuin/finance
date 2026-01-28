from typing import List, Optional
import re

from ..core.models import Asset, AssetType, Market
from ..services.index_service import index_service
from .fetcher import fetcher


class SearchProvider:
    async def search(self, keyword: str) -> List[Asset]:
        # 1. Try Local Search First
        results = index_service.search_local(keyword)
        if results:
            return results

        # 2. Fallback to API Search
        results = await self._do_search(keyword)

        # If no results, try stripping prefixes
        if not results:
            # Common prefixes: HK, US, SH, SZ, CN, JP, DE, GLOBAL
            match = re.match(
                r"^(?:HK|US|SH|SZ|CN|JP|DE|GLOBAL)(.+)$", keyword, re.IGNORECASE
            )
            if match:
                stripped_keyword = match.group(1)
                # print(f"DEBUG: Smart strip '{keyword}' -> '{stripped_keyword}'")
                results = await self._do_search(stripped_keyword)

        return results

    async def _do_search(self, keyword: str) -> List[Asset]:
        results = []

        # EastMoney Search
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": keyword,
            "type": "14",
            "token": "D43BF722C8E33BDC906FB84D85E326E8",
            "count": "10",
        }

        try:
            data = await fetcher.fetch(url, params=params)
            if (
                data
                and "QuotationCodeTable" in data
                and "Data" in data["QuotationCodeTable"]
            ):
                items = data["QuotationCodeTable"]["Data"]
                if items:
                    for item in items:
                        asset = self._parse_em_item(item)
                        if asset:
                            # Avoid duplicates (check code and market to distinguish between SZ000001 and SH000001)
                            # Or just check api_code which is unique per provider's view
                            if not any(r.api_code == asset.api_code for r in results):
                                results.append(asset)
        except Exception as e:
            print(f"Search error: {e}")

        return results

    def _parse_em_item(self, item: dict) -> Optional[Asset]:
        # Parse EastMoney item
        # SecurityType: 1(沪A), 2(深A), 7(美股), 17(基金), 11(指数)
        # Classify: AStock, UsStock, OTCFUND, HKStock

        code = item.get("Code")
        name = item.get("Name")
        classify = item.get("Classify")
        sec_type = item.get("SecurityType")
        market_type = item.get("MarketType")  # 1=SH, 2=SZ

        if not code or not name:
            return None

        # Determine Market and Type
        market = None
        asset_type = None
        api_code = code

        if classify == "AStock":
            market = Market.CN
            asset_type = AssetType.STOCK
            # Construct API code for Sina (sh/sz prefix)
            if market_type == "1":
                api_code = f"sh{code}"
            elif market_type == "2":
                api_code = f"sz{code}"
            else:
                # Fallback based on code
                api_code = f"sh{code}" if code.startswith("6") else f"sz{code}"

        elif classify == "UsStock":
            market = Market.US
            asset_type = AssetType.STOCK
            api_code = f"gb_{code.lower()}"

        elif classify == "OTCFUND":
            market = Market.CN
            asset_type = AssetType.FUND
            api_code = code  # Fund code is enough for EM API

        elif classify == "HKStock":
            market = Market.HK
            asset_type = AssetType.STOCK
            api_code = f"hk{code}"

        elif classify == "HK":
            # HK Index (e.g. HSI)
            market = Market.HK
            asset_type = AssetType.INDEX
            api_code = f"rt_hk{code}"  # Assuming rt_hk prefix for indices like HSI

        elif classify == "Index":
            # A-Share Indices (e.g. 000001)
            market = Market.CN
            asset_type = AssetType.INDEX
            if market_type == "1":
                api_code = f"sh{code}"
            elif market_type == "2":
                api_code = f"sz{code}"
            else:
                api_code = f"sh{code}"  # Default to sh

        elif classify == "UniversalIndex":
            # EM Indices (Global)
            # Accept if it looks like a valid global index
            quote_id = item.get("QuoteID", "")
            if quote_id.startswith("100."):
                market = Market.GLOBAL
                asset_type = AssetType.INDEX
                api_code = quote_id  # e.g. 100.SPX, 100.HSI

            # Handle CN Indices that might appear here
            elif code.isdigit() and len(code) == 6:
                market = Market.CN
                asset_type = AssetType.INDEX
                if code.startswith("000"):
                    api_code = f"sh{code}"
                elif code.startswith("399"):
                    api_code = f"sz{code}"
                else:
                    return None
            else:
                return None

        else:
            # Check for Bonds?
            # 931446 is CSI Index, usually handled as Index
            if code.startswith("93"):
                market = Market.CN
                asset_type = AssetType.INDEX
                api_code = f"csi{code}"  # Special handling might be needed
            else:
                return None

        if market and asset_type:
            return Asset(
                code=code, api_code=api_code, name=name, market=market, type=asset_type
            )
        return None


search_provider = SearchProvider()
