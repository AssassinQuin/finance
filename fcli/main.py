#!/usr/bin/env python3
"""FCLI - 命令行金融工具"""

import typer
import asyncio
from datetime import datetime
from typing import Optional, List

from .core.config import config
from .core.database import Database
from .core.storage import storage
from .core.models import Asset, Market, AssetType
from .services.gold_service import gold_service
from .services.gpr_service import gpr_service
from .services.forex_service import forex_service
from .services.quote_service import quote_service
from .infra.http_client import http_client
from .utils.presenter import ConsolePresenter

app = typer.Typer(
    help="FCLI - 命令行金融工具",
    add_completion=False,
    rich_markup_mode="rich",
)

# ============ Quote (Default) ============


@app.callback(invoke_without_command=True)
def quote(ctx: typer.Context):
    """查询自选行情 (默认命令)"""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_fetch_quotes())


async def _fetch_quotes() -> None:
    assets = await storage.load()
    if not assets:
        ConsolePresenter.print_warning("暂无自选。使用 'fcli add <代码>' 添加。")
        return
    quotes = await quote_service.fetch_all(assets)
    if quotes:
        ConsolePresenter.print_quote_table(quotes)
    else:
        ConsolePresenter.print_warning("获取行情失败。")
    await http_client.close()


# ============ Watchlist ============


@app.command()
def add(codes: List[str]):
    """添加自选"""

    async def _add() -> int:
        count = 0
        for code in codes:
            market = Market.CN if code.isdigit() or code.startswith(("6", "0", "3")) else Market.US
            asset = Asset(code=code, name=code, market=market, type=AssetType.STOCK)
            if await storage.add(asset):
                count += 1
        return count

    count = asyncio.run(_add())
    ConsolePresenter.print_success(f"已添加 {count} 个自选")


@app.command()
def rm(code: str):
    """删除自选"""

    async def _rm() -> bool:
        return await storage.remove(code)

    if asyncio.run(_rm()):
        ConsolePresenter.print_success(f"已删除 {code}")
    else:
        ConsolePresenter.print_error(f"未找到 {code}")


@app.command()
def ls():
    """列出所有自选"""
    assets = asyncio.run(storage.load())
    ConsolePresenter.print_asset_table(assets)


# ============ Gold ============


@app.command()
def gold(
    update: bool = typer.Option(False, "-u", "--update", help="强制更新"),
):
    """全球黄金储备 - 显示 1月、3月、6月、12月变化"""
    asyncio.run(_gold(update))


async def _gold(update: bool) -> None:
    """执行黄金储备查询，    
    流程:
        1. 从数据库获取数据
        2. 如果不是上月最新数据，自动从 IMF 更新
        3. 展示多时间段变化 (1m, 3m, 6m, 12m)
    """
    try:
        # 初始化数据库连接
        await gold_service.init_database()
        
        # 获取最新数据（自动检测并更新过期数据）
        reserves = await gold_service.fetch_all_with_auto_update(force=update)
        reserves = await gold_service.fetch_all_with_auto_update(force=update)

        if not reserves:
            ConsolePresenter.print_warning("无法获取黄金储备数据")
            return

        # 展示数据
        ConsolePresenter.print_gold_report(
            {
                "reserves": reserves,
                "balance": None,  # IMF 不提供 supply/demand 数据
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )
    finally:
        await gold_service.close()
        if Database.is_enabled():
            await Database.close()


# ============ GPR ============


@app.command()
def gpr(
    chart: bool = typer.Option(True, "--chart/--no-chart", help="显示图表"),
):
    """地缘政治风险指数"""
    analysis = gpr_service.get_gpr_analysis()
    if not analysis:
        ConsolePresenter.print_warning("暂无 GPR 数据")
        return
    ConsolePresenter.print_gpr_report(analysis)
    if chart:
        history = gpr_service.get_gpr_history(months=120)
        ConsolePresenter.print_gpr_chart(history)


# ============ Forex ============


@app.command()
def fx(
    base: str = typer.Argument("USD", help="基准货币"),
    quote: Optional[str] = typer.Argument(None, help="目标货币"),
):
    """汇率查询"""
    asyncio.run(_fx(base, quote))


async def _fx(base: str, quote: Optional[str]) -> None:
    try:
        if quote:
            rate = await forex_service.get_rate(base, quote)
            if rate:
                print(f"\n{base}/{quote}: {rate.rate:.4f}\n")
            else:
                ConsolePresenter.print_error(f"无法获取 {base}/{quote}")
        else:
            rates = await forex_service.get_all_rates(base)
            if rates:
                print(f"\n{base} 汇率表:\n")
                for code, r in sorted(rates.items(), key=lambda x: x[1].rate, reverse=True):
                    print(f"  {code}: {r.rate:.4f}")
                print()
            else:
                ConsolePresenter.print_error(f"无法获取 {base} 汇率")
    finally:
        await http_client.close()


# ============ Search ============


@app.command()
def find(keyword: str):
    """搜索资产"""
    ConsolePresenter.print_warning("搜索功能暂不可用")


if __name__ == "__main__":
    app()
