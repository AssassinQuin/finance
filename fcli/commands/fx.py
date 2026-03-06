import asyncio

import typer

from ..services.forex_service import forex_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="汇率查询")


@app.callback(invoke_without_command=True)
def rate(
    base: str = typer.Argument("USD", help="基准货币"),
    quote: str | None = typer.Argument(None, help="目标货币"),
):
    """汇率查询 (默认命令)

    示例:
        fcli fx              # 查询 USD 汇率
        fcli fx USD CNY      # 查询 USD/CNY 汇率
        fcli fx EUR          # 查询 EUR 汇率
    """
    asyncio.run(_rate(base, quote))


async def _rate(base: str, quote: str | None) -> None:
    if quote:
        with ConsolePresenter.status(f"查询 {base}/{quote} 汇率..."):
            rate = await forex_service.get_rate(base, quote)
        if rate:
            print(f"\n{base}/{quote}: {rate.rate:.4f}\n")
        else:
            ConsolePresenter.print_error(f"无法获取 {base}/{quote}")
    else:
        with ConsolePresenter.status(f"获取 {base} 汇率..."):
            rates = await forex_service.get_all_rates(base)
        if rates:
            print(f"\n{base} 汇率表:\n")
            for code, r in sorted(rates.items(), key=lambda x: x[1].rate, reverse=True):
                display = forex_service.format_currency_display(code)
                print(f"  {display}: {r.rate:.4f}")
            print()
        else:
            ConsolePresenter.print_error(f"无法获取 {base} 汇率")
