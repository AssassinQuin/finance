import asyncio

import typer

from ..infra.http_client import http_client
from ..services.forex_service import forex_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="汇率查询")


@app.callback(invoke_without_command=True)
def rate(
    base: str = typer.Argument("USD", help="基准货币"),
    quote: str | None = typer.Argument(None, help="目标货币"),
):
    """汇率查询 (默认命令)

    查询货币汇率。单参数返回该货币对所有主要货币汇率，
    双参数返回两者之间的汇率。

    示例:
        fcli fx              # USD 对所有货币
        fcli fx CNY          # CNY 对所有货币
        fcli fx USD CNY      # USD/CNY 汇率
    """
    asyncio.run(_rate(base, quote))


async def _rate(base: str, quote: str | None) -> None:
    from ..core.config import config
    from ..core.database import Database

    try:
        # Initialize database for cache support
        await Database.init(config)

        if quote:
            rate = await forex_service.get_rate(base, quote)
            if rate:
                print(f"\n{base}/{quote}: {rate.rate:.4f}\n")
            else:
                ConsolePresenter.print_error(f"无法获取 {base}/{quote}")
        else:
            rates = await forex_service.get_all_rates(base)
            if rates:
                print(f"\n{base} 汇率表:\n")
                for code, r in sorted(rates.items(), key=lambda x: x[1].rate, reverse=True):
                    display = forex_service.format_currency_display(code)
                    print(f"  {display}: {r.rate:.4f}")
                print()
            else:
                ConsolePresenter.print_error(f"无法获取 {base} 汇率")
    finally:
        await http_client.close()
        await Database.close()


@app.command()
def list():
    """列出支持的货币"""
    ConsolePresenter.print_warning("此功能暂未实现")
