import typer
import asyncio
from datetime import datetime

from ..core.database import Database
from ..services.gold_service import gold_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="黄金数据")


@app.callback(invoke_without_command=True)
def reserves(
    update: bool = typer.Option(False, "-u", "--update", help="强制更新数据"),
):
    """全球黄金储备报告 (默认命令)

    显示各国央行黄金储备及多时间段变化 (1月、3月、6月、12月)。

    示例:
        fcli gold              # 查询黄金储备
        fcli gold -u           # 强制更新数据
    """
    asyncio.run(_reserves(update))


async def _reserves(update: bool) -> None:
    try:
        await gold_service.init_database()
        reserves = await gold_service.fetch_all_with_auto_update(force=update)
        if not reserves:
            ConsolePresenter.print_warning("无法获取黄金储备数据")
            return

        balance = await gold_service.fetch_global_supply_demand()
        ConsolePresenter.print_gold_report(
            {
                "reserves": reserves,
                "balance": balance,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )
    finally:
        await gold_service.close()
        if Database.is_enabled():
            await Database.close()


@app.command()
def supply():
    """黄金供需数据"""
    asyncio.run(_supply())


async def _supply():
    try:
        await gold_service.init_database()
        balance = await gold_service.fetch_global_supply_demand()
        if balance:
            ConsolePresenter.print_success(f"黄金供需数据: {balance}")
        else:
            ConsolePresenter.print_warning("无法获取黄金供需数据")
    finally:
        await gold_service.close()
        if Database.is_enabled():
            await Database.close()
