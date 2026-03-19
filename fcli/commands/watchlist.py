import asyncio

import typer

from ..core.container import container
from ..services.watchlist_service import watchlist_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="自选股管理", context_settings={"help_option_names": ["-h", "--help"]})


@app.callback(invoke_without_command=True)
def query_quotes(ctx: typer.Context):
    """查询所有自选股行情 (默认命令)

    示例:
        fcli watchlist
    """
    if ctx.invoked_subcommand is not None:
        return

    async def _query():
        try:
            with ConsolePresenter.status("获取自选股行情..."):
                assets = await watchlist_service.list_assets()
                if not assets:
                    ConsolePresenter.print_warning("自选股列表为空，使用 'fcli watchlist add <代码>' 添加")
                    return
                quotes = await container.quote_service.fetch_all(assets)
            ConsolePresenter.print_quote_table(quotes)
        finally:
            await container.cleanup()

    asyncio.run(_query())


@app.command()
def add(codes: list[str]):
    """添加自选股

    支持同时添加多个代码。

    示例:
        fcli watchlist add 600519
        fcli watchlist add 600519 000858
    """

    async def _add() -> int:
        with ConsolePresenter.status("添加自选股..."):
            count = await watchlist_service.add_assets(codes)
        return count

    count = asyncio.run(_add())
    ConsolePresenter.print_success(f"已添加 {count} 个自选")


@app.command()
def rm(codes: list[str]):
    """删除自选股

    支持同时删除多个代码。

    示例:
        fcli watchlist rm 600519
        fcli watchlist rm 600519 000858
    """

    async def _rm() -> int:
        with ConsolePresenter.status("删除自选股..."):
            count = await watchlist_service.remove_assets(codes)
        return count

    count = asyncio.run(_rm())
    ConsolePresenter.print_success(f"已删除 {count} 个自选")


@app.command()
def ls():
    """列出所有自选股

    示例:
        fcli watchlist ls
    """

    async def _ls():
        with ConsolePresenter.status("获取自选股列表..."):
            assets = await watchlist_service.list_assets()
        ConsolePresenter.print_asset_table(assets)

    asyncio.run(_ls())


@app.command()
def clear():
    """清空所有自选股

    示例:
        fcli watchlist clear
    """
    ConsolePresenter.print_warning("此功能暂未实现")
