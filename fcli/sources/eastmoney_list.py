import asyncio
from typing import List

from ..core.models import Asset, AssetType, Market
from ..providers.fetcher import fetcher


class EastMoneyListSource:
    """
    Fetches full lists of assets from EastMoney.
    """

    async def fetch_global_indices(self) -> List[Asset]:
        """Fetch global indices (major world indices)."""
        # EastMoney Global Indices List
        # Try a simpler API or just fetch all global indices under 'mi:100' (Global Index Market)
        # fs=m:2 indicates Global Market in some contexts, but let's try broader fs
        # 'i:100' is major indices. Let's try to find USD Index (UDI) specifically if it's missing.
        # UDI is often under '100' or '101'.

        # New attempt: Fetch broader list
        # Found UDI in m:100 (Global Index Market)
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "2000",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:100",  # Market 100 covers global indices in EM (Verified via curl)
            "fields": "f12,f13,f14",
        }

        assets = []
        try:
            data = await fetcher.fetch(url, params=params)
            # EM API sometimes returns non-standard JSON structure or errors
            # print(f"DEBUG: Global indices data type: {type(data)}")

            if (
                data
                and isinstance(data, dict)
                and "data" in data
                and data["data"]
                and "diff" in data["data"]
            ):
                items = data["data"]["diff"]
                # items can be a list or a dict in some EM APIs
                if isinstance(items, dict):
                    items = items.values()

                for item in items:
                    code = item.get("f12")
                    name = item.get("f14")
                    market_id = item.get("f13")

                    if not code or not name:
                        continue

                    # Construct API Code: market_id.code (e.g. 100.SPX)
                    api_code = f"{market_id}.{code}"

                    assets.append(
                        Asset(
                            code=code,
                            api_code=api_code,
                            name=name,
                            market=Market.GLOBAL,
                            type=AssetType.INDEX,
                        )
                    )
        except Exception as e:
            print(f"Error fetching global indices: {e}")

        return assets

    async def fetch_cn_funds(self) -> List[Asset]:
        """Fetch all CN Funds."""
        # This is a large list (10k+), maybe just fetch top active or implement paging if needed.
        # For now, let's try a large page size, EM usually supports it.
        url = "http://fund.eastmoney.com/js/fundcode_search.js"

        assets = []
        try:
            # This returns a JS array: var r = [[...],...]
            text = await fetcher.fetch(url, text_mode=True)
            # Simple parsing
            # Content is like: var r = [["000001","HXCZHH","华夏成长混合","混合型","HUAXIACHENGZHANGHUNHE"],...]
            import json

            start = text.find("[[")
            end = text.rfind("]]")
            if start != -1 and end != -1:
                json_str = text[start : end + 2]
                items = json.loads(json_str)

                for item in items:
                    # item: [code, pinyin_abbr, name, type, pinyin_full]
                    if len(item) >= 3:
                        code = item[0]
                        name = item[2]

                        assets.append(
                            Asset(
                                code=code,
                                api_code=code,
                                name=name,
                                market=Market.CN,
                                type=AssetType.FUND,
                            )
                        )
        except Exception as e:
            print(f"Error fetching funds: {e}")

        return assets

    async def fetch_cn_stocks(self) -> List[Asset]:
        """Fetch A-Shares."""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "10000",  # Fetch all in one go if possible
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",  # SH/SZ A-Shares
            "fields": "f12,f14,f13",
        }

        assets = []
        try:
            data = await fetcher.fetch(url, params=params)
            if data and "data" in data and data["data"] and "diff" in data["data"]:
                items = data["data"]["diff"]
                for item in items:
                    code = item.get("f12")
                    name = item.get("f14")
                    market_id = item.get("f13")  # 1=SH, 0=SZ

                    if not code or not name:
                        continue

                    # Construct Sina API code
                    api_code = f"sh{code}" if market_id == 1 else f"sz{code}"

                    assets.append(
                        Asset(
                            code=code,
                            api_code=api_code,
                            name=name,
                            market=Market.CN,
                            type=AssetType.STOCK,
                        )
                    )
        except Exception as e:
            print(f"Error fetching CN stocks: {e}")

        return assets

    async def fetch_all(self) -> List[Asset]:
        """Fetch all supported assets concurrently."""
        tasks = [
            self.fetch_global_indices(),
            self.fetch_cn_stocks(),
            self.fetch_cn_funds(),
        ]
        results = await asyncio.gather(*tasks)
        all_assets = []
        for res in results:
            all_assets.extend(res)
        return all_assets


eastmoney_list_source = EastMoneyListSource()
