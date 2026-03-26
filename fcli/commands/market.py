"""Market command - fund search and detail."""

from typing import Annotated

import typer

from ..core.database import Database
from ..core.models import Fund, FundDetail, FundType
from ..core.stores import FundStore
from ..infra.http_client import run_async
from ..services.fund_service import fund_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="基金市场 (search/detail)")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """FCLI - 命令行金融工具"""
    pass


@app.command()
def search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="搜索关键词 (代码或名称)")],
    type: Annotated[str | None, typer.Option(help="基金类型: INDEX/ETF/FUND")] = None,
    limit: Annotated[int, typer.Option(help="返回结果数量")] = 20,
):
    """搜索基金."""
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
    ctx: typer.Context,
    code: Annotated[str, typer.Argument(help="基金代码")],
):
    """查看基金详情."""
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
    ctx: typer.Context,
    type: Annotated[str | None, typer.Option("--type", "-t", help="基金类型: INDEX/ETF/FUND")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="强制更新，跳过月度检查")] = False,
):
    """更新基金数据."""
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
    await Database.init()
    try:
        funds = await FundStore.search(query, fund_type, limit)
        return funds
    finally:
        await Database.close()


async def _get_fund_detail(code: str) -> FundDetail | None:
    """Get fund detail from database or scrape."""
    await Database.init()
    try:
        fund = await FundStore.get_by_code(code)
        if not fund:
            return None

        scale_history = await FundStore.get_scale_history(code)

        return FundDetail(
            code=fund.code,
            name=fund.name,
            name_short=fund.name_short,
            fund_type=fund.fund_type,
            market=fund.market,
            invest_type=fund.invest_type,
            management_fee=fund.management_fee,
            custody_fee=fund.custody_fee,
            fund_company=fund.fund_company,
            tracking_index=fund.tracking_index,
            inception_date=fund.inception_date,
            listing_date=fund.listing_date,
            scale=fund.scale,
            share=fund.share,
            nav=fund.nav,
            scale_date=fund.scale_date,
            is_active=fund.is_active,
            extra=fund.extra,
            scale_history=scale_history,
        )
    finally:
        await Database.close()


async def _update_fund_data(type: str | None, force: bool) -> int:
    """Update fund data from scraper."""
    await Database.init()
    try:
        count = await fund_service.update_fund_data(type, force=force)
        return count
    finally:
        await Database.close()
