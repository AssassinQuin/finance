#!/usr/bin/env python3
"""FCLI - 命令行金融工具"""

import atexit
import asyncio

import typer

from .commands.fx import app as fx_app
from .commands.gold import app as gold_app
from .commands.gpr import app as gpr_app
from .commands.watchlist import app as watchlist_app
from .core.database import Database
from .infra.http_client import http_client

app = typer.Typer(
    name="fcli",
    help="FCLI - 命令行金融工具",
    add_completion=False,
    rich_markup_mode="rich",
)


def cleanup():
    """应用退出时自动清理资源"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if Database.is_enabled():
            loop.run_until_complete(Database.close())

        loop.run_until_complete(http_client.close())

        loop.close()
    except Exception:
        pass


atexit.register(cleanup)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """FCLI - 命令行金融工具

    默认行为：查询所有自选行情 (等同于 'fcli watchlist ls')
    """
    if ctx.invoked_subcommand is None:
        print("使用 'fcli watchlist ls' 查看自选股")


app.add_typer(watchlist_app, name="watchlist", help="自选股管理 (add/rm/ls)")
app.add_typer(gold_app, name="gold", help="黄金数据 (reserves/supply)")
app.add_typer(gpr_app, name="gpr", help="地缘政治风险指数 (index/history)")
app.add_typer(fx_app, name="fx", help="汇率查询 (rate/list)")

if __name__ == "__main__":
    app()
