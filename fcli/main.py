import typer
import asyncio
from datetime import datetime
from .cli.commands.quote import quote as quote_cmd
from .cli.commands.asset import app as asset_app
from .cli.commands.market import app as market_app
from .cli.commands.forex import app as forex_app
from .cli.commands.search import app as search_app
from .cli.commands.system import app as system_app
from .services.gold_service import gold_service
from .services.gpr_service import gpr_service
from .utils.presenter import ConsolePresenter
from .infra.http_client import http_client
from .core.database import Database

app = typer.Typer(
    help="FCLI - 命令行金融工具",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"max_content_width": 120},
)

app.add_typer(asset_app, name="watch", help="自选资产管理 (add/list/remove)")
app.add_typer(market_app, name="market", help="市场数据")
app.add_typer(forex_app, name="forex", help="汇率查询")
app.add_typer(search_app, name="search", help="搜索资产")
app.add_typer(system_app, name="系统管理")

app.command(name="quote", help="查询股票/基金实时行情")(quote_cmd)


async def gold_async(
    update: bool = typer.Option(False, "--update", "-u", help="强制从 API 更新数据"),
    detail: bool = typer.Option(False, "--detail", "-d", help="显示详细供需平衡表"),
    history: str = typer.Option(
        None, "--history", "-h", help="查看特定国家的历史趋势 (如 CN, US)"
    ),
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


def gold_cli(**kwargs):
    asyncio.run(gold_async(**kwargs))


app.command(name="gold", help="全球黄金储备")(gold_cli)


async def gpr_async(
    chart: bool = typer.Option(
        True, "--chart/--no-chart", "-c", help="是否显示历史趋势折线图"
    ),
):
    analysis = gpr_service.get_gpr_analysis()
    if not analysis:
        ConsolePresenter.print_warning("暂无 GPR 数据。")
        return

    ConsolePresenter.print_gpr_report(analysis)

    if chart:
        history = gpr_service.get_gpr_history(months=120)
        ConsolePresenter.print_gpr_chart(history)


def gpr_cli(**kwargs):
    asyncio.run(gpr_async(**kwargs))


app.command(name="gpr", help="地缘政治风险指数")(gpr_cli)
