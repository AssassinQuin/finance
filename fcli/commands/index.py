import asyncio

import typer

from ..providers.fetcher import fetcher
from ..services.index_service import index_service

app = typer.Typer(help="管理本地资产索引")


@app.callback(invoke_without_command=True)
def update():
    """
    更新本地资产索引 (从全网拉取最新股票、基金、指数列表)
    """

    async def _do_update():
        try:
            await index_service.build_index()
        finally:
            await fetcher.close()

    asyncio.run(_do_update())
