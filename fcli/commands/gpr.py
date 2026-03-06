import asyncio

import typer

from ..core.config import config
from ..core.database import Database
from ..services.gpr_service import gpr_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="地缘政治风险指数")


@app.callback(invoke_without_command=True)
def index(
    update: bool = typer.Option(False, "-u", "--update", help="强制更新数据"),
    chart: bool = typer.Option(True, "--chart/--no-chart", help="显示图表"),
):
    """地缘政治风险指数 (默认命令)

    显示 GPR 指数分析报告和历史趋势图。

    示例:
        fcli gpr              # 查询 GPR 指数
        fcli gpr -u           # 强制更新数据
        fcli gpr --no-chart   # 不显示图表
    """
    asyncio.run(_index(update, chart))


async def _index(update: bool, chart: bool) -> None:
    try:
        if update:
            await Database.init(config)
            result = await gpr_service.update_data()
            if result.get("success"):
                ConsolePresenter.print_success(f"已更新GPR数据: {result.get('records', 0)} 条记录")
            else:
                ConsolePresenter.print_error(f"更新失败: {result.get('error', 'Unknown error')}")
                return

        analysis = gpr_service.get_gpr_analysis()
        if not analysis:
            ConsolePresenter.print_warning("暂无 GPR 数据")
            return

        ConsolePresenter.print_gpr_report(analysis)

        if chart:
            history = gpr_service.get_gpr_history(months=120)
            ConsolePresenter.print_gpr_chart(history)
    finally:
        if Database.is_enabled():
            await Database.close()


@app.command()
def history(
    months: int = typer.Option(120, "-m", "--months", help="显示月数"),
):
    """GPR 历史趋势"""
    data = gpr_service.get_gpr_history(months=months)
    if data:
        ConsolePresenter.print_gpr_chart(data)
    else:
        ConsolePresenter.print_warning("暂无历史数据")
