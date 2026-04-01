"""Market command - fund search and detail."""

from typing import Annotated

import typer

from ..core.config import config
from ..core.database import Database
from ..core.models import Fund, FundDetail, FundType
from ..core.stores import FundStore
from ..infra.http_client import run_async
from ..core.container import container
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="基金市场", context_settings={"help_option_names": ["-h", "--help"]})


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """基金市场 (默认命令)

    示例:
        fcli market
    """
    pass


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="搜索关键词 (代码或名称)")],
    type: Annotated[str | None, typer.Option("--type", "-t", help="基金类型 (INDEX/ETF/FUND)")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="返回结果数量")] = 20,
):
    """搜索基金

    示例:
        fcli market search 沪深 300
        fcli market search 510300 -t ETF
        fcli market search 黄金 -n 5
    """
    try:
        fund_type_enum = None
        if type:
            fund_type_enum = FundType(type.upper())

        funds = run_async(_search_funds(query, fund_type_enum, limit))

        if not funds:
            ConsolePresenter.print_warning("未找到匹配的基金")
            return

        ConsolePresenter.print_fund_table(funds)
    except Exception as e:
        ConsolePresenter.print_error(f"搜索失败: {e}")
        raise typer.Exit(1) from e


@app.command()
def detail(
    code: Annotated[str, typer.Argument(help="基金代码")],
):
    """查看基金详情

    示例:
        fcli market detail 510300
    """
    try:
        fund_detail = run_async(_get_fund_detail(code))

        if not fund_detail:
            ConsolePresenter.print_error(f"未找到基金: {code}")
            return

        ConsolePresenter.print_fund_detail(fund_detail)
    except Exception as e:
        ConsolePresenter.print_error(f"查询失败: {e}")
        raise typer.Exit(1) from e


@app.command()
def update(
    type: Annotated[str | None, typer.Option("--type", "-t", help="基金类型 (INDEX/ETF/FUND)")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="强制更新")] = False,
):
    """更新基金数据

    示例:
        fcli market update
        fcli market update -t ETF
        fcli market update -f
    """
    try:
        ConsolePresenter.print_info("正在更新基金数据...")
        count = run_async(_update_fund_data(type, force))

        if count > 0:
            ConsolePresenter.print_success(f"成功更新 {count} 只基金")
        else:
            ConsolePresenter.print_warning("未更新任何基金")
    except Exception as e:
        ConsolePresenter.print_error(f"更新失败: {e}")
        raise typer.Exit(1) from e


async def _search_funds(query: str, fund_type: FundType | None, limit: int) -> list[Fund]:
    """Search funds from database."""
    async with Database.session(config):
        funds = await FundStore.search(query, fund_type, limit)
        return funds


async def _get_fund_detail(code: str) -> FundDetail | None:
    """Get fund detail from database or scrape."""
    async with Database.session(config):
        fund = await FundStore.get_by_code(code)
        if not fund:
            return None

        scale_history = await FundStore.get_scale_history(code)
        return FundDetail.from_fund(fund, scale_history)


async def _update_fund_data(type: str | None, force: bool) -> int:
    """Update fund data from scraper."""
    async with Database.session(config):
        count = await container.fund_service.update_fund_data(type, force=force)
        return count
