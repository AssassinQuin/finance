import typer

from ..core.config import config
from ..core.container import container
from ..core.database import Database
from ..infra.http_client import run_async
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="汇率查询", context_settings={"help_option_names": ["-h", "--help"]})


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
    run_async(_rate(base, quote))


async def _rate(base: str, quote: str | None) -> None:
    async with Database.session(config):
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
