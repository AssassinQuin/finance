from typing import Annotated

import typer

from ..core.container import container
from ..utils.command import run_command
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="汇率查询", context_settings={"help_option_names": ["-h", "--help"]})


@app.callback(invoke_without_command=True)
def rate(
    base: Annotated[str, typer.Argument(help="基准货币")] = "USD",
    quote: Annotated[str | None, typer.Argument(help="目标货币")] = None,
):
    """汇率查询 (默认命令)

    示例:
        fcli fx              # 查询 USD 汇率
        fcli fx USD CNY      # 查询 USD/CNY 汇率
        fcli fx EUR          # 查询 EUR 汇率
    """
    run_command(_rate(base, quote), "获取汇率失败")


async def _rate(base: str, quote: str | None) -> None:
    async with container.session():
        if quote:
            with ConsolePresenter.status(f"查询 {base}/{quote} 汇率..."):
                rate = await container.forex_service.get_rate(base, quote)
            if rate:
                ConsolePresenter.print_exchange_rate(rate)
            else:
                ConsolePresenter.print_error(f"无法获取 {base}/{quote}")
        else:
            with ConsolePresenter.status(f"获取 {base} 汇率..."):
                rates_dict = await container.forex_service.get_all_rates(base)
            if rates_dict:
                rates_list = list(rates_dict.values())
                ConsolePresenter.print_exchange_rates(rates_list, base)
            else:
                ConsolePresenter.print_error(f"无法获取 {base} 汇率")
