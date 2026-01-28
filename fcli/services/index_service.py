import json
from pathlib import Path
from typing import List

from ..core.config import config
from ..core.models import Asset
from ..sources.eastmoney_list import eastmoney_list_source
from ..utils.presenter import ConsolePresenter


class IndexService:
    def __init__(self):
        self.index_file = config.data_dir / "index.json"
        self._ensure_dir()

    def _ensure_dir(self):
        if not config.data_dir.exists():
            config.data_dir.mkdir(parents=True)

    async def build_index(self):
        """Fetch all assets and save to local index file."""
        ConsolePresenter.print_success("开始更新本地资产索引，这可能需要几秒钟...")
        
        assets = await eastmoney_list_source.fetch_all()
        
        # Save to JSON
        with open(self.index_file, "w") as f:
            json.dump(
                [asset.model_dump(mode="json") for asset in assets],
                f,
                ensure_ascii=False,
                indent=None # Compact for speed
            )
            
        ConsolePresenter.print_success(f"索引更新完成！共收录 {len(assets)} 条资产数据。")

    def load_index(self) -> List[Asset]:
        """Load index from file."""
        if not self.index_file.exists():
            return []
            
        try:
            with open(self.index_file, "r") as f:
                data = json.load(f)
                return [Asset(**item) for item in data]
        except Exception as e:
            ConsolePresenter.print_error(f"读取索引失败: {e}")
            return []

    def search_local(self, keyword: str, limit: int = 10) -> List[Asset]:
        """
        Search in local index.
        Supports matching code (startswith) or name (contains).
        """
        all_assets = self.load_index()
        if not all_assets:
            return []
            
        keyword = keyword.upper()
        results = []
        
        # 1. Exact Code Match (Priority 1)
        for asset in all_assets:
            if asset.code.upper() == keyword:
                results.append(asset)
        
        # 2. StartsWith Code (Priority 2)
        for asset in all_assets:
            if asset.code.upper().startswith(keyword) and asset not in results:
                results.append(asset)
                if len(results) >= limit:
                    return results
                    
        # 3. Name Contains (Priority 3)
        for asset in all_assets:
            if keyword in asset.name.upper() and asset not in results:
                results.append(asset)
                if len(results) >= limit:
                    return results
                    
        return results

index_service = IndexService()
