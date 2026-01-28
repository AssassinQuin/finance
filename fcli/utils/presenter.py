from typing import List

from rich import box
from rich.console import Console
from rich.table import Table

from ..core.models import Asset, Quote

console = Console()

MARKET_MAP = {
    "CN": "沪深",
    "HK": "港股",
    "US": "美股",
    "FUND": "基金",
    "GLOBAL": "全球",
    "FOREX": "外汇",
    "BOND": "债券",
}

TYPE_MAP = {
    "STOCK": "股票",
    "FUND": "基金",
    "INDEX": "指数",
    "FOREX": "外汇",
    "BOND": "债券",
}

TYPE_COLOR = {
    "STOCK": "yellow",
    "FUND": "magenta",
    "INDEX": "blue",
    "FOREX": "cyan",
    "BOND": "white",
}


class ConsolePresenter:
    @staticmethod
    def print_asset_table(assets: List[Asset]):
        table = Table(box=box.SIMPLE, header_style="bold cyan")
        table.add_column("代码", justify="left", style="green")
        table.add_column("名称", justify="left")
        table.add_column("市场", justify="center")
        table.add_column("类型", justify="center")

        for asset in assets:
            market_cn = MARKET_MAP.get(asset.market.value, asset.market.value)
            type_cn = TYPE_MAP.get(asset.type.value, asset.type.value)
            type_color = TYPE_COLOR.get(asset.type.value, "white")

            table.add_row(
                asset.code,
                asset.name,
                market_cn,
                f"[{type_color}]{type_cn}[/{type_color}]",
            )
        console.print(table)

    @staticmethod
    def print_quote_table(quotes: List[Quote]):
        table = Table(box=box.SIMPLE, header_style="bold cyan")
        table.add_column("代码", justify="left", style="green")
        table.add_column("名称", justify="left")
        table.add_column("最新价", justify="right")
        table.add_column("涨跌幅", justify="right")
        table.add_column("更新时间", justify="right")
        table.add_column("市场", justify="center")
        table.add_column("类型", justify="center")

        for quote in quotes:
            # Colorize change percent
            change_str = f"{quote.change_percent:+.2f}%"
            if quote.change_percent > 0:
                change_style = "bold red"
            elif quote.change_percent < 0:
                change_style = "bold green"
            else:
                change_style = "white"

            market_cn = MARKET_MAP.get(quote.market.value, quote.market.value)
            type_cn = TYPE_MAP.get(quote.type.value, quote.type.value)
            type_color = TYPE_COLOR.get(quote.type.value, "white")

            table.add_row(
                quote.code,
                quote.name,
                f"{quote.price:.2f}",
                f"[{change_style}]{change_str}[/{change_style}]",
                quote.update_time,
                market_cn,
                f"[{type_color}]{type_cn}[/{type_color}]",
            )
        console.print(table)

    @staticmethod
    def print_search_table(assets: List[Asset]):
        table = Table(box=box.SIMPLE, header_style="bold cyan", title="搜索结果")
        table.add_column("代码", justify="left", style="green")
        table.add_column("名称", justify="left")
        table.add_column("市场", justify="center")
        table.add_column("类型", justify="center")
        table.add_column("API Code", justify="left", style="dim")

        for asset in assets:
            market_cn = MARKET_MAP.get(asset.market.value, asset.market.value)
            type_cn = TYPE_MAP.get(asset.type.value, asset.type.value)

            table.add_row(asset.code, asset.name, market_cn, type_cn, asset.api_code)
        console.print(table)

    @staticmethod
    def print_success(message: str):
        console.print(f"[green]{message}[/green]")

    @staticmethod
    def print_error(message: str):
        console.print(f"[red]{message}[/red]")

    @staticmethod
    def print_warning(message: str):
        console.print(f"[yellow]{message}[/yellow]")

    @staticmethod
    def status(message: str):
        return console.status(f"[bold green]{message}[/bold green]")
