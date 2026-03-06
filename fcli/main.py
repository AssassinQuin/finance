#!/usr/bin/env python3
"""FCLI - 命令行金融工具"""

import asyncio

import typer

from .commands.fx import app as fx_app
from .commands.gold import app as gold_app
from .commands.gpr import app as gpr_app
from .commands.watchlist import app as watchlist_app
from .core.config import symbol_registry
from .core.container import container
from .core.models.asset import Asset
from .utils.presenter import ConsolePresenter

app = typer.Typer(
    name="fcli",
    help="FCLI - 命令行金融工具",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.command(name="quote", deprecated=False)
def quote_cmd(
    codes: list[str] | None = typer.Argument(None, help="股票代码列表"),
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


async def _fetch_quotes(codes: list[str] | None = None) -> None:
    from .core.config import config
    from .core.database import Database

    try:
        await Database.init(config)

        if codes:
            assets = []
            for c in codes:
                market = symbol_registry.infer_market(c)
                api_code = symbol_registry.resolve_api_code(c, market)
                asset_type = symbol_registry.infer_type(c)
                assets.append(
                    Asset(
                        code=c,
                        market=market,
                        type=asset_type,
                        api_code=api_code,
                        name=c,
                    )
                )
        else:
            from .services.watchlist_service import watchlist_service

            assets = await watchlist_service.list_assets()
            if not assets:
                ConsolePresenter.print_warning("暂无自选。使用 'fcli watchlist add <代码>' 添加。")
                return

        try:
            quotes = await container.quote_service.fetch_all(assets)
            if quotes:
                ConsolePresenter.print_quote_table(quotes)
            else:
                ConsolePresenter.print_warning("获取行情失败 - 返回空数据")
        except Exception as e:
            ConsolePresenter.print_error(f"获取行情失败: {e}")
            import traceback

            traceback.print_exc()
    finally:
        await Database.close()
        await container.cleanup()


app.add_typer(watchlist_app, name="watchlist", help="自选股管理 (add/rm/ls)")
app.add_typer(gold_app, name="gold", help="黄金数据 (reserves/supply)")
app.add_typer(gpr_app, name="gpr", help="地缘政治风险指数 (index/history)")
app.add_typer(fx_app, name="fx", help="汇率查询 (rate/list)")

if __name__ == "__main__":
    app()
