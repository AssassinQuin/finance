import asyncio
import typer
from ..services.gpr_service import gpr_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="地缘政治风险 (GPR) 分析")

@app.callback(invoke_without_command=True)
def gpr(
    chart: bool = typer.Option(True, "--chart/--no-chart", "-c", help="是否显示历史趋势折线图")
):
    """
    查看全球地缘政治风险 (GPR) 指数及其多维度变动分析。
    """
    analysis = gpr_service.get_gpr_analysis()
    if not analysis:
        ConsolePresenter.print_warning("暂无 GPR 数据。")
        return

    # 1. Show GPR Analysis Table
    ConsolePresenter.print_gpr_report(analysis)
    
    if chart:
        history = gpr_service.get_gpr_history(months=120) # Show 10 years for full context
        ConsolePresenter.print_gpr_chart(history)

if __name__ == "__main__":
    app()
