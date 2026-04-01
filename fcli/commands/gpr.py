from typing import Annotated

import typer

from ..core.config import config
from ..core.container import container
from ..core.database import Database
from ..infra.http_client import run_async
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="地缘政治风险指数", context_settings={"help_option_names": ["-h", "--help"]})


@app.callback(invoke_without_command=True)
def index(
    update: Annotated[bool, typer.Option("-u", "--update", help="强制更新数据")] = False,
    chart: Annotated[bool, typer.Option("--chart/--no-chart", help="显示图表")] = True,
):
    """地缘政治风险指数 (默认命令)

    显示 GPR 指数分析报告和历史趋势图。

    示例:
        fcli gpr              # 查询 GPR 指数
        fcli gpr -u           # 强制更新数据
        fcli gpr --no-chart   # 不显示图表
    """
    try:
        run_async(_index(update, chart))
    except Exception as e:
        ConsolePresenter.print_error(f"获取 GPR 数据失败: {e}")
        raise typer.Exit(1) from e


async def _index(update: bool, chart: bool) -> None:
    async with Database.session(config):
        if update:
            with ConsolePresenter.status("更新 GPR 数据..."):
                result = await container.gpr_service.update_data()
            if result.get("success"):
                ConsolePresenter.print_success(f"已更新 GPR 数据：{result.get('records', 0)} 条记录")
            else:
                ConsolePresenter.print_error(f"更新失败：{result.get('error', 'Unknown error')}")
                return

        with ConsolePresenter.status("获取 GPR 分析报告..."):
            analysis = await container.gpr_service.get_gpr_analysis()
        if not analysis:
            ConsolePresenter.print_warning("暂无 GPR 数据")
            return

        ConsolePresenter.print_gpr_report(analysis)

        if chart:
            with ConsolePresenter.status("获取历史数据..."):
                history = await container.gpr_service.get_gpr_history(months=120)
            ConsolePresenter.print_gpr_chart(history)


@app.command()
def history(
    months: Annotated[int, typer.Option("-m", "--months", help="显示月数")] = 120,
):
    """GPR 历史趋势

    示例:
        fcli gpr history
        fcli gpr history -m 60
    """
    try:
        run_async(_history(months))
    except Exception as e:
        ConsolePresenter.print_error(f"获取历史数据失败: {e}")
        raise typer.Exit(1) from e


async def _history(months: int) -> None:
    async with Database.session(config):
        with ConsolePresenter.status("获取历史数据..."):
            data = await container.gpr_service.get_gpr_history(months=months)
        if data:
            ConsolePresenter.print_gpr_chart(data)
        else:
            ConsolePresenter.print_warning("暂无历史数据")
