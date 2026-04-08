from rich import box
from rich.table import Table

from ..core.models import Asset, Quote
from .base_presenter import BasePresenter, console
from .time_util import DATETIME_FORMAT


class QuotePresenter(BasePresenter):
    @staticmethod
    def print_asset_table(assets: list[Asset]):
        table = Table(box=box.SIMPLE, header_style="bold cyan")
        table.add_column("代码", justify="left", style="green")
        table.add_column("名称", justify="left")
        table.add_column("市场", justify="center")
        table.add_column("类型", justify="center")

        for asset in assets:
            market_cn = QuotePresenter._get_market_display(asset.market.value)
            type_cn, type_color = QuotePresenter._get_type_display(asset.type.value)

            table.add_row(
                asset.code,
                asset.name,
                market_cn,
                f"[{type_color}]{type_cn}[/{type_color}]",
            )
        console.print(table)

    @staticmethod
    def print_quote_table(quotes: list[Quote]):
        table = Table(box=box.SIMPLE, header_style="bold cyan")
        table.add_column("#", justify="center", style="dim", width=2)
        table.add_column("代码", justify="left", style="green")
        table.add_column("名称", justify="left")
        table.add_column("最新价", justify="right")
        table.add_column("涨跌幅", justify="right")
        table.add_column("更新时间", justify="right")
        table.add_column("市场", justify="center")
        table.add_column("类型", justify="center")

        sorted_quotes = sorted(quotes, key=lambda q: q.change_percent, reverse=True)

        for i, quote in enumerate(sorted_quotes, 1):
            change_str = f"{quote.change_percent:+.2f}%"
            if quote.change_percent > 0:
                change_style = "bold red"
            elif quote.change_percent < 0:
                change_style = "bold green"
            else:
                change_style = "white"

            market_cn = QuotePresenter._get_market_display(quote.market.value)
            type_cn, type_color = QuotePresenter._get_type_display(quote.type.value)

            table.add_row(
                str(i),
                quote.code,
                quote.name,
                f"{quote.price:.2f}",
                f"[{change_style}]{change_str}[/{change_style}]",
                quote.update_time.strftime(DATETIME_FORMAT),
                market_cn,
                f"[{type_color}]{type_cn}[/{type_color}]",
            )
        console.print(table)

    @staticmethod
    def print_search_table(assets: list[Asset]):
        table = Table(box=box.SIMPLE, header_style="bold cyan", title="搜索结果")
        table.add_column("代码", justify="left", style="green")
        table.add_column("名称", justify="left")
        table.add_column("市场", justify="center")
        table.add_column("类型", justify="center")
        table.add_column("API Code", justify="left", style="dim")

        for asset in assets:
            market_cn = QuotePresenter._get_market_display(asset.market.value)
            type_cn, _ = QuotePresenter._get_type_display(asset.type.value)

            table.add_row(asset.code, asset.name, market_cn, type_cn, asset.api_code)
        console.print(table)
