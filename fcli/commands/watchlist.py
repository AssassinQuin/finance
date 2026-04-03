from typing import Annotated

import typer

from ..core.container import container
from ..utils.command import run_command
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
    run_command(_query(), "获取行情失败")


async def _query():
    async with container.session():
        with ConsolePresenter.status("获取自选股行情..."):
            assets = await container.watchlist_service.list_assets()
            if not assets:
                ConsolePresenter.print_warning("自选股列表为空，使用 'fcli watchlist add <代码>' 添加")
                return
            quotes = await container.quote_service.fetch_all(assets)
    ConsolePresenter.print_quote_table(quotes)


@app.command()
def add(
    codes: Annotated[list[str], typer.Argument(help="股票代码 (支持多个)")],
):
    """添加自选股

    支持同时添加多个代码。

    示例:
        fcli watchlist add 600519
        fcli watchlist add 600519 000858
    """
    count = run_command(_add(codes), "添加失败")
    ConsolePresenter.print_success(f"已添加 {count} 个自选")


async def _add(codes: list[str]) -> int:
    async with container.session():
        with ConsolePresenter.status("添加自选股..."):
            count = await container.watchlist_service.add_assets(codes)
        return count


@app.command()
def rm(
    codes: Annotated[list[str], typer.Argument(help="股票代码 (支持多个)")],
):
    """删除自选股

    支持同时删除多个代码。

    示例:
        fcli watchlist rm 600519
        fcli watchlist rm 600519 000858
    """
    count = run_command(_rm(codes), "删除失败")
    ConsolePresenter.print_success(f"已删除 {count} 个自选")


async def _rm(codes: list[str]) -> int:
    async with container.session():
        with ConsolePresenter.status("删除自选股..."):
            count = await container.watchlist_service.remove_assets(codes)
        return count


@app.command()
def ls():
    """列出所有自选股

    示例:
        fcli watchlist ls
    """
    run_command(_ls(), "获取列表失败")


async def _ls():
    async with container.session():
        with ConsolePresenter.status("获取自选股列表..."):
            assets = await container.watchlist_service.list_assets()
        ConsolePresenter.print_asset_table(assets)


@app.command()
def clear():
    """清空所有自选股

    示例:
        fcli watchlist clear
    """
    count = run_command(_clear(), "清空失败")
    if count > 0:
        ConsolePresenter.print_success(f"已清空 {count} 个自选")
    else:
        ConsolePresenter.print_warning("自选股列表为空")


async def _clear() -> int:
    async with container.session():
        with ConsolePresenter.status("清空自选股..."):
            count = await container.watchlist_service.clear_all()
        return count
