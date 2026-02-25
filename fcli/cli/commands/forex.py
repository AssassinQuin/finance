"""汇率查询命令"""

import typer
import asyncio
from typing import Optional

from ...services.forex_service import forex_service
from ...infra.http_client import http_client
from ...utils.presenter import ConsolePresenter
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


async def fetch_forex(from_currency: str, to_currency: Optional[str] = None):
    """获取汇率数据"""
    if to_currency:
        # 单一汇率查询
        rate = await forex_service.get_rate(from_currency, to_currency)
        if rate:
            _print_single_rate(rate)
        else:
            ConsolePresenter.print_error(f"无法获取 {from_currency} -> {to_currency} 的汇率")
    else:
        # 获取所有常用货币汇率
        rates = await forex_service.get_all_rates(from_currency)
        if rates:
            _print_rates_table(from_currency, rates)
        else:
            ConsolePresenter.print_error(f"无法获取 {from_currency} 的汇率数据")
    
    await http_client.close()


def _print_single_rate(rate):
    """打印单一汇率"""
    from_name = forex_service.get_currency_name(rate.from_currency)
    to_name = forex_service.get_currency_name(rate.to_currency)
    
    console.print(f"\n[bold cyan]汇率查询结果[/bold cyan]")
    console.print(f"[green]{rate.from_currency}[/green] ({from_name}) -> [green]{rate.to_currency}[/green] ({to_name})")
    console.print(f"[bold yellow]汇率: {rate.rate:.4f}[/bold yellow]")
    console.print(f"[dim]日期: {rate.date} | 数据源: {rate.source}[/dim]\n")


def _print_rates_table(base_currency: str, rates: dict):
    """打印汇率表格"""
    table = Table(
        title=f"\n{base_currency} ({forex_service.get_currency_name(base_currency)}) 汇率表",
        show_header=True,
        header_style="bold cyan",
    )
    
    table.add_column("货币代码", style="green", width=10)
    table.add_column("货币名称", width=15)
    table.add_column("汇率", justify="right", style="yellow")
    table.add_column("反向汇率", justify="right", style="dim")
    
    # 按汇率排序
    sorted_rates = sorted(rates.items(), key=lambda x: x[1].rate, reverse=True)
    
    for code, rate in sorted_rates:
        name = forex_service.get_currency_name(code)
        inverse = 1 / rate.rate if rate.rate > 0 else 0
        
        table.add_row(
            code,
            name,
            f"{rate.rate:.4f}",
            f"{inverse:.4f}",
        )
    
    console.print(table)
    
    # 打印更新时间
    if rates:
        first_rate = list(rates.values())[0]
        console.print(f"[dim]数据日期: {first_rate.date} | 数据源: {first_rate.source}[/dim]\n")


@app.callback(invoke_without_command=True)
def forex(
    from_currency: str = typer.Argument(
        "USD",
        help="基准货币代码 (如 USD, CNY, EUR)"
    ),
    to_currency: Optional[str] = typer.Argument(
        None,
        help="目标货币代码 (可选，不指定则显示所有常用货币汇率)"
    ),
):
    """
    汇率查询
    
    示例:
        python run.py forex USD        # 查看 USD 对所有常用货币的汇率
        python run.py forex USD CNY    # 查看 USD -> CNY 的汇率
        python run.py forex EUR        # 查看 EUR 对所有常用货币的汇率
    """
    asyncio.run(fetch_forex(from_currency, to_currency))
