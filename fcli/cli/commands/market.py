import typer
import asyncio
from datetime import datetime
from ...services.gold_service import gold_service
from ...services.gpr_service import gpr_service
from ...utils.presenter import ConsolePresenter
from ...infra.http_client import http_client
from ...core.database import Database

app = typer.Typer()


@app.command("gold")
def gold_cmd(
    update: bool = typer.Option(False, "--update", "-u", help="强制更新数据"),
    detail: bool = typer.Option(False, "--detail", "-d", help="显示详细信息"),
    history: str = typer.Option(None, "--history", "-h", help="查看历史趋势 (国家代码)"),
):
    asyncio.run(gold_impl(update=update, detail=detail, history=history))


async def gold_impl(
    update: bool = False,
    detail: bool = False,
    history: str = None,
):
    try:
        if history:
            history_value = str(history)
            history_data = await gold_service.get_history(
                history_value.upper(), months=24
            )
            if history_data:
                print(f"\n{history_value.upper()} 历史黄金储备趋势:\n")
                for h in reversed(history_data):
                    print(f"  {h['date']}: {h['amount']:.2f} 吨")
            else:
                ConsolePresenter.print_warning(f"暂无 {history_value.upper()} 历史数据")
            return

        reserves = await gold_service.fetch_all_with_auto_update(force=update)
        balance = await gold_service.fetch_global_supply_demand()

        for r in reserves:
            r["change_1m"] = r.get("change_1m", 0.0)
            r["change_1y"] = r.get("change_1y", 0.0)

        last_update = datetime.now().strftime("%Y-%m-%d %H:%M")

        report_data = {
            "reserves": reserves,
            "balance": balance,
            "last_update": last_update,
        }

        ConsolePresenter.print_gold_report(report_data)

        if update:
            ConsolePresenter.print_success(f"数据已更新: {last_update}")
    finally:
        await http_client.close()
        if Database.is_enabled():
            await Database.close()


@app.command("gpr")
def gpr_cmd(
    chart: bool = typer.Option(True, "--chart/--no-chart", help="显示图表"),
):
    asyncio.run(gpr_impl(chart=chart))


async def gpr_impl(chart: bool = True):
    analysis = gpr_service.get_gpr_analysis()
    if not analysis:
        ConsolePresenter.print_warning("暂无 GPR 数据。")
        return

    ConsolePresenter.print_gpr_report(analysis)

    if chart:
        history = gpr_service.get_gpr_history(months=120)
        ConsolePresenter.print_gpr_chart(history)
