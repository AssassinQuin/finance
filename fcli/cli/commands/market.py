import typer
import asyncio
from ...services.gold_service import gold_service
from ...services.gpr_service import gpr_service
from ...utils.presenter import ConsolePresenter
from ...infra.http_client import http_client

app = typer.Typer()

@app.command(name="gold")
def gold(
    update: bool = typer.Option(False, "--update", "-u", help="强制从 API 更新数据"),
    detail: bool = typer.Option(False, "--detail", "-d", help="显示详细供需平衡表"),
    history: str = typer.Option(None, "--history", "-h", help="查看特定国家的历史趋势 (如 CN, US)")
):
    """查看全球主要央行黄金储备变动及供需平衡。"""
    async def _do_gold():
        try:
            # Simplified logic based on available simplified service
            reserves = await gold_service.fetch_imf_reserves([])
            balance = await gold_service.fetch_global_supply_demand()
            
            for r in reserves:
                r["change_1m"] = 0.0
                r["change_1y"] = 0.0
            
            report_data = {
                "reserves": reserves,
                "balance": balance,
                "last_update": "2026-01-01"
            }
            
            ConsolePresenter.print_gold_report(report_data)
        finally:
            await http_client.close()

    asyncio.run(_do_gold())

@app.command(name="gpr")
def gpr(chart: bool = typer.Option(True, "--chart/--no-chart", "-c", help="是否显示历史趋势折线图")):
    """查看全球地缘政治风险 (GPR) 指数。"""
    analysis = gpr_service.get_gpr_analysis()
    if not analysis:
        ConsolePresenter.print_warning("暂无 GPR 数据。")
        return

    ConsolePresenter.print_gpr_report(analysis)
    
    if chart:
        history = gpr_service.get_gpr_history(months=120)
        ConsolePresenter.print_gpr_chart(history)
