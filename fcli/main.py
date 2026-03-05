#!/usr/bin/env python3
"""FCLI - 命令行金融工具"""

import typer
import asyncio
from typing import Optional, List

from .core.models.base import Market, AssetType
from .core.models.asset import Asset
from .services.quote_service import quote_service
from .services.watchlist_service import watchlist_service
from .infra.http_client import http_client
from .utils.presenter import ConsolePresenter
from .commands.watchlist import app as watchlist_app
from .commands.gold import app as gold_app
from .commands.gpr import app as gpr_app
from .commands.fx import app as fx_app

app = typer.Typer(
    name="fcli",
    help="FCLI - 命令行金融工具",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.command(name="quote", deprecated=False)
def quote_cmd(
    codes: Optional[List[str]] = typer.Argument(None, help="股票代码列表"),
):
    """查询自选行情

    不带参数时显示所有自选，带参数时查询指定代码行情。

    示例:
        fcli quote              # 查询所有自选
        fcli quote 600519       # 查询贵州茅台
        fcli quote 600519 AAPL  # 查询多个代码
    """
    asyncio.run(_fetch_quotes(codes))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """FCLI - 命令行金融工具

    默认行为: 查询所有自选行情 (等同于 'fcli quote')
    """
    if ctx.invoked_subcommand is None:
        asyncio.run(_fetch_quotes(None))


async def _fetch_quotes(codes: Optional[List[str]] = None) -> None:
    if codes:
        assets = [Asset(code=c, market=Market.CN, type=AssetType.STOCK, api_code=c, name=c) for c in codes]
    else:
        assets = await watchlist_service.list_assets()
        if not assets:
            ConsolePresenter.print_warning("暂无自选。使用 'fcli watchlist add <代码>' 添加。")
            return

    try:
        quotes = await quote_service.fetch_all(assets)
        if quotes:
            ConsolePresenter.print_quote_table(quotes)
        else:
            ConsolePresenter.print_warning("获取行情失败 - 返回空数据")
    except Exception as e:
        ConsolePresenter.print_error(f"获取行情失败: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await http_client.close()


app.add_typer(watchlist_app, name="watchlist", help="自选股管理 (add/rm/ls)")
app.add_typer(gold_app, name="gold", help="黄金数据 (reserves/supply)")
app.add_typer(gpr_app, name="gpr", help="地缘政治风险指数 (index/history)")
app.add_typer(fx_app, name="fx", help="汇率查询 (rate/list)")

if __name__ == "__main__":
    app()
