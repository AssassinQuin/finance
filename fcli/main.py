#!/usr/bin/env python3

import asyncio

import typer

from .commands.fx import app as fx_app
from .commands.gold import app as gold_app
from .commands.gpr import app as gpr_app
from .commands.watchlist import app as watchlist_app

app = typer.Typer(
    name="fcli",
    help="FCLI - 命令行金融工具",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """FCLI - 命令行金融工具

    默认行为：查询所有自选行情 (等同于 'fcli watchlist')
    """
    if ctx.invoked_subcommand is not None:
        return

    from .core.container import container
    from .services.watchlist_service import watchlist_service
    from .utils.presenter import ConsolePresenter

    async def _query_quotes():
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

    asyncio.run(_query_quotes())


app.add_typer(watchlist_app, name="watchlist", help="自选股管理 (add/rm/ls)")
app.add_typer(gold_app, name="gold", help="黄金数据 (reserves/supply)")
app.add_typer(gpr_app, name="gpr", help="地缘政治风险指数 (index/history)")
app.add_typer(fx_app, name="fx", help="汇率查询 (rate/list)")

if __name__ == "__main__":
    app()
