from datetime import datetime
from typing import Annotated

import typer

from ..core.container import container
from ..utils.command import run_command
from ..utils.presenter import ConsolePresenter
from ..utils.time_util import DATETIME_FORMAT

app = typer.Typer(help="黄金数据", context_settings={"help_option_names": ["-h", "--help"]})


@app.callback(invoke_without_command=True)
def reserves(
    ctx: typer.Context,
    update: Annotated[bool, typer.Option("-u", "--update", help="强制更新数据")] = False,
):
    """全球黄金储备报告 (默认命令)

    显示各国央行黄金储备及多时间段变化 (1月、3月、6月、12月)。

    示例:
        fcli gold              # 查询黄金储备
        fcli gold -u           # 强制更新数据
    """
    if ctx.invoked_subcommand is not None:
        return
    run_command(_reserves(update), "获取黄金储备失败")


async def _reserves(update: bool) -> None:
    async with container.session():
        status_msg = "强制更新数据..." if update else "获取黄金储备数据..."
        with ConsolePresenter.status(status_msg):
            reserves = await container.gold_reserve_service.fetch_all_with_auto_update(force=update)

        if not reserves:
            ConsolePresenter.print_warning("无法获取黄金储备数据")
            return

        with ConsolePresenter.status("获取供需数据..."):
            balance = await container.gold_supply_demand_service.fetch_global_supply_demand()

        ConsolePresenter.print_gold_report(
            {
                "reserves": reserves,
                "balance": balance,
                "last_update": datetime.now().strftime(DATETIME_FORMAT),
            }
        )


@app.command()
def supply(
    update: Annotated[bool, typer.Option("-u", "--update", help="强制更新供需数据")] = False,
):
    """黄金供需数据

    示例:
        fcli gold supply
        fcli gold supply -u
    """
    run_command(_supply(update), "获取供需数据失败")


async def _supply(update: bool):
    async with container.session():
        status_msg = "强制更新黄金供需数据..." if update else "获取黄金供需数据..."
        with ConsolePresenter.status(status_msg):
            balance = await container.gold_supply_demand_service.fetch_global_supply_demand(force_update=update)
        if balance:
            ConsolePresenter.print_gold_supply_balance(balance)
        else:
            ConsolePresenter.print_warning("无法获取黄金供需数据")
