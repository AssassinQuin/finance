import asyncio

import typer

from ..providers.fetcher import fetcher
from ..providers.search import search_provider
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="搜索金融资产")


@app.callback(invoke_without_command=True)
def search(keyword: str):
    """
    搜索资产 (支持股票、基金、指数等)
    """

    async def _do_search():
        try:
            results = await search_provider.search(keyword)
            if not results:
                ConsolePresenter.print_warning("未找到相关结果。")
                return
            ConsolePresenter.print_search_table(results)
        finally:
            await fetcher.close()

    asyncio.run(_do_search())
