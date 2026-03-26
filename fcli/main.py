#!/usr/bin/env python3

import typer

from .commands.fx import app as fx_app
from .commands.gold import app as gold_app
from .commands.gpr import app as gpr_app
from .commands.market import app as market_app
from .commands.watchlist import app as watchlist_app

app = typer.Typer(
    name="fcli",
    help="FCLI - 命令行金融工具",
    add_completion=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """FCLI - 命令行金融工具

    默认行为：查询所有自选行情 (等同于 'fcli watchlist')
    """
    if ctx.invoked_subcommand is not None:
        return

    from .commands.watchlist import query_quotes

    query_quotes(ctx)


app.add_typer(watchlist_app, name="watchlist", help="自选股管理 (add/rm/ls)")
app.add_typer(market_app, name="market", help="基金市场 (search/detail)")
app.add_typer(gold_app, name="gold", help="黄金数据 (reserves/supply)")
app.add_typer(gpr_app, name="gpr", help="地缘政治风险指数 (index/history)")
app.add_typer(fx_app, name="fx", help="汇率查询 (rate/list)")

if __name__ == "__main__":
    app()
