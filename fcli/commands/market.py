"""Market command - fund search and detail."""

from typing import Annotated

import typer

from ..core.container import container
from ..core.models import Fund, FundDetail, FundType
from ..utils.command import run_command
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="基金市场", context_settings={"help_option_names": ["-h", "--help"]})


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """基金市场 (默认命令)

    示例:
        fcli market
    """
    if ctx.invoked_subcommand is not None:
        return
    ConsolePresenter.print_info("使用以下子命令操作基金市场:")
    ConsolePresenter.print_info("  fcli market search <关键词>  搜索基金")
    ConsolePresenter.print_info("  fcli market detail <代码>    查看基金详情")
    ConsolePresenter.print_info("  fcli market update           更新基金数据")
    ConsolePresenter.print_info("使用 -h 查看详细帮助")


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
    fund_type_enum = None
    if type:
        fund_type_enum = FundType(type.upper())

    funds = run_command(_search_funds(query, fund_type_enum, limit), "搜索失败")

    if not funds:
        ConsolePresenter.print_warning("未找到匹配的基金")
        return

    ConsolePresenter.print_fund_table(funds)


@app.command()
def detail(
    code: Annotated[str, typer.Argument(help="基金代码")],
):
    """查看基金详情

    示例:
        fcli market detail 510300
    """
    fund_detail = run_command(_get_fund_detail(code), "查询失败")

    if not fund_detail:
        ConsolePresenter.print_error(f"未找到基金: {code}")
        return

    ConsolePresenter.print_fund_detail(fund_detail)


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
    ConsolePresenter.print_info("正在更新基金数据...")
    count = run_command(_update_fund_data(type, force), "更新失败")

    if count > 0:
        ConsolePresenter.print_success(f"成功更新 {count} 只基金")
    else:
        ConsolePresenter.print_warning("未更新任何基金")


async def _search_funds(query: str, fund_type: FundType | None, limit: int) -> list[Fund]:
    async with container.session():
        return await container.fund_service.search(query, fund_type, limit)


async def _get_fund_detail(code: str) -> FundDetail | None:
    async with container.session():
        return await container.fund_service.get_detail(code)


async def _update_fund_data(type: str | None, force: bool) -> int:
    async with container.session():
        return await container.fund_service.update_fund_data(type, force=force)
