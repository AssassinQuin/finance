import typer
import asyncio
from datetime import datetime
from ...services.gold_service import gold_service
from ...services.gpr_service import gpr_service
from ...services.spdr_service import spdr_service
from ...utils.presenter import ConsolePresenter
from ...infra.http_client import http_client
from ...core.database import Database

app = typer.Typer()


@app.command("gold")
def gold_cmd(
    update: bool = typer.Option(False, "--update", "-u", help="强制更新数据"),
    detail: bool = typer.Option(False, "--detail", "-d", help="显示详细信息"),
    history: str = typer.Option(None, "--history", "-h", help="查看历史趋势 (国家代码)"),
    china: bool = typer.Option(False, "--china", "-c", help="查看中国近5年历史"),
):
    asyncio.run(gold_impl(update=update, detail=detail, history=history, china=china))


async def gold_impl(
    update: bool = False,
    detail: bool = False,
    history: str = None,
    china: bool = False,
):
    try:
        # 查看中国历史数据
        if china:
            print("\n🇨🇳 中国央行黄金储备近5年变化:\n")
            history_data = await gold_service.get_china_history_online(months=60)
            if history_data:
                prev = None
                print(f"{'日期':<12} {'储备量(吨)':<12} {'月变化':<10} {'趋势'}")
                print("-" * 50)
                for h in reversed(history_data):
                    change = ""
                    trend = ""
                    if prev:
                        diff = h['amount'] - prev
                        change = f"+{diff:.2f}" if diff > 0 else f"{diff:.2f}"
                        trend = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
                    print(f"{h['date']:<12} {h['amount']:<12.2f} {change:<10} {trend}")
                    prev = h['amount']
            else:
                ConsolePresenter.print_warning("无法获取中国黄金储备历史数据")
            return
        
        # 查看特定国家历史
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
        
        # 获取央行储备数据
        reserves = await gold_service.fetch_all_with_auto_update(force=update)
        balance = await gold_service.fetch_global_supply_demand()
        
        # 获取 SPDR 持仓数据
        spdr_summary = await spdr_service.get_summary()

        for r in reserves:
            r["change_1m"] = r.get("change_1m", 0.0)
            r["change_1y"] = r.get("change_1y", 0.0)

        last_update = datetime.now().strftime("%Y-%m-%d %H:%M")

        report_data = {
            "reserves": reserves,
            "balance": balance,
            "spdr": spdr_summary,
            "last_update": last_update,
        }

        ConsolePresenter.print_gold_report_v2(report_data)

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
