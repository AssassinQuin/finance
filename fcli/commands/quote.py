import asyncio

import typer

from ..core.storage import storage
from ..providers.fetcher import fetcher
from ..services.quote_service import quote_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="获取实时行情")


@app.callback(invoke_without_command=True)
def quote(force: bool = typer.Option(False, "--force", "-f", help="强制刷新")):
    """
    获取所有自选资产的实时行情
    """

    async def _do_quote():
        try:
            assets = storage.load()
            if not assets:
                ConsolePresenter.print_warning("暂无资产，请使用 'add' 命令添加。")
                return

            with ConsolePresenter.status("正在获取实时行情..."):
                quotes = await quote_service.get_quotes(assets)

            ConsolePresenter.print_quote_table(quotes)
        finally:
            await fetcher.close()

    asyncio.run(_do_quote())
