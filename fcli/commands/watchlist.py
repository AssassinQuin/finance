import asyncio

import typer

from ..core.config import config
from ..core.database import Database
from ..services.watchlist_service import watchlist_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="自选股管理")


async def _init_db():
    await Database.init(config)


async def _close_db():
    await Database.close()


@app.callback(invoke_without_command=True)
def list_assets():
    """列出所有自选股 (默认命令)"""

    async def _list():
        try:
            await _init_db()
            assets = await watchlist_service.list_assets()
            ConsolePresenter.print_asset_table(assets)
        finally:
            await _close_db()

    asyncio.run(_list())


@app.command()
def add(codes: list[str]):
    """添加自选股

    支持同时添加多个代码。

    示例:
        fcli watchlist add 600519
        fcli watchlist add 600519 000858
    """

    async def _add() -> int:
        try:
            await _init_db()
            return await watchlist_service.add_assets(codes)
        finally:
            await _close_db()

    count = asyncio.run(_add())
    ConsolePresenter.print_success(f"已添加 {count} 个自选")


@app.command()
def rm(code: str):
    """删除自选股

    示例:
        fcli watchlist rm 600519
    """

    async def _rm() -> bool:
        try:
            await _init_db()
            return await watchlist_service.remove_asset(code)
        finally:
            await _close_db()

    if asyncio.run(_rm()):
        ConsolePresenter.print_success(f"已删除 {code}")
    else:
        ConsolePresenter.print_error(f"未找到 {code}")


@app.command()
def ls():
    """列出所有自选股"""

    async def _ls():
        try:
            await _init_db()
            assets = await watchlist_service.list_assets()
            ConsolePresenter.print_asset_table(assets)
        finally:
            await _close_db()

    asyncio.run(_ls())


@app.command()
def clear():
    """清空所有自选股"""
    ConsolePresenter.print_warning("此功能暂未实现")
