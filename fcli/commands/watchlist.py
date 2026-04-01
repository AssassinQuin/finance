from typing import Annotated

import typer

from ..core.config import config
from ..core.container import container
from ..core.database import Database
from ..infra.http_client import run_async
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
    try:
        run_async(_query())
    except Exception as e:
        ConsolePresenter.print_error(f"获取行情失败: {e}")
        raise typer.Exit(1) from e


async def _query():
    async with Database.session(config):
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
    try:

        async def _add() -> int:
            async with Database.session(config):
                with ConsolePresenter.status("添加自选股..."):
                    count = await container.watchlist_service.add_assets(codes)
                return count

        count = run_async(_add())
        ConsolePresenter.print_success(f"已添加 {count} 个自选")
    except Exception as e:
        ConsolePresenter.print_error(f"添加失败: {e}")
        raise typer.Exit(1) from e


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
    try:

        async def _rm() -> int:
            async with Database.session(config):
                with ConsolePresenter.status("删除自选股..."):
                    count = await container.watchlist_service.remove_assets(codes)
                return count

        count = run_async(_rm())
        ConsolePresenter.print_success(f"已删除 {count} 个自选")
    except Exception as e:
        ConsolePresenter.print_error(f"删除失败: {e}")
        raise typer.Exit(1) from e


@app.command()
def ls():
    """列出所有自选股

    示例:
        fcli watchlist ls
    """
    try:

        async def _ls():
            async with Database.session(config):
                with ConsolePresenter.status("获取自选股列表..."):
                    assets = await container.watchlist_service.list_assets()
                ConsolePresenter.print_asset_table(assets)

        run_async(_ls())
    except Exception as e:
        ConsolePresenter.print_error(f"获取列表失败: {e}")
        raise typer.Exit(1) from e


@app.command()
def clear():
    """清空所有自选股

    示例:
        fcli watchlist clear
    """
    try:

        async def _clear() -> int:
            async with Database.session(config):
                with ConsolePresenter.status("清空自选股..."):
                    count = await container.watchlist_service.clear_all()
                return count

        count = run_async(_clear())
        if count > 0:
            ConsolePresenter.print_success(f"已清空 {count} 个自选")
        else:
            ConsolePresenter.print_warning("自选股列表为空")
    except Exception as e:
        ConsolePresenter.print_error(f"清空失败: {e}")
        raise typer.Exit(1) from e
