import asyncio
from typing import List

import typer

from ..core.storage import storage
from ..providers.fetcher import fetcher
from ..providers.search import search_provider
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="管理自选资产 (添加/删除/列表)")


@app.command("add")
def add(codes: List[str]):
    """
    添加资产 (自动搜索并匹配最佳结果)
    """

    async def _do_add():
        try:
            for code in codes:
                # 1. Search
                results = await search_provider.search(code)

                if not results:
                    ConsolePresenter.print_error(f"未找到相关资产: {code}")
                    continue

                # 2. Pick best match (exact code match preferred)
                match = None

                # Try exact match on 'code' first
                for r in results:
                    if r.code.upper() == code.upper():
                        match = r
                        break

                # If code is SHxxxxxx or SZxxxxxx, try to match api_code
                if not match and (
                    code.upper().startswith("SH") or code.upper().startswith("SZ")
                ):
                    for r in results:
                        if r.api_code.upper() == code.upper():
                            match = r
                            break

                if not match:
                    match = results[0]  # Fallback to first
                    ConsolePresenter.print_warning(
                        f"未找到精确匹配 {code}, 使用 {match.name} ({match.code})"
                    )

                # 3. Save
                storage.add(match)
                ConsolePresenter.print_success(f"已添加: {match.name} ({match.code})")
        finally:
            await fetcher.close()

    asyncio.run(_do_add())


@app.command("remove")
def remove(code: str):
    """
    删除资产
    """
    if storage.remove(code):
        ConsolePresenter.print_success(f"已删除 {code}")
    else:
        ConsolePresenter.print_error(f"未找到代码 {code}")


@app.command("list")
def list_assets():
    """
    列出所有自选资产
    """
    assets = storage.load()
    if not assets:
        ConsolePresenter.print_warning("暂无资产，请使用 'add' 命令添加。")
        return
    ConsolePresenter.print_asset_table(assets)
