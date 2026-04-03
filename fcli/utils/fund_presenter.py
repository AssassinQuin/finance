from rich import box
from rich.panel import Panel
from rich.table import Table

from ..core.models import ExchangeRate, Fund, FundDetail
from .base_presenter import BasePresenter, console


class FundPresenter(BasePresenter):
    @staticmethod
    def print_fund_table(funds: list[Fund]):
        type_labels = {"INDEX": "指数基金(场外)", "ETF": "场内ETF", "FUND": "场外基金"}
        table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            title="基金搜索结果",
        )
        table.add_column("#", justify="center", style="dim", width=2)
        table.add_column("代码", justify="left", style="green", width=8)
        table.add_column("名称", justify="left", width=30)
        table.add_column("类型", justify="center", width=16)
        table.add_column("投资类型", justify="center", width=10)
        table.add_column("规模(亿)", justify="right", width=10)
        table.add_column("管理费", justify="right", width=8)
        table.add_column("托管费", justify="right", width=8)

        for i, fund in enumerate(funds, 1):
            type_color = {"INDEX": "blue", "ETF": "yellow", "FUND": "magenta"}.get(fund.fund_type.value, "white")
            type_label = type_labels.get(fund.fund_type.value, fund.fund_type.value)
            invest_str = fund.invest_type.value if fund.invest_type else "-"
            scale_str = f"{fund.scale:.2f}" if fund.scale else "-"
            mgmt_fee_str = f"{fund.management_fee * 100:.2f}%" if fund.management_fee else "-"
            custody_fee_str = f"{fund.custody_fee * 100:.2f}%" if fund.custody_fee else "-"

            table.add_row(
                str(i),
                fund.code,
                fund.name[:28] + "..." if len(fund.name) > 30 else fund.name,
                f"[{type_color}]{type_label}[/{type_color}]",
                invest_str,
                scale_str,
                mgmt_fee_str,
                custody_fee_str,
            )
        console.print(table)

    @staticmethod
    def print_fund_detail(fund: FundDetail):
        type_labels = {"INDEX": "指数基金(场外)", "ETF": "场内ETF", "FUND": "场外基金"}
        type_label = type_labels.get(fund.fund_type.value, fund.fund_type.value)
        lines = []
        lines.append(f"[bold cyan]{fund.code}[/bold cyan] - {fund.name}")
        lines.append("")
        lines.append("[bold]基本信息[/bold]")
        lines.append(f"  基金类型: {type_label}")
        lines.append(f"  投资类型: {fund.invest_type.value if fund.invest_type else '-'}")
        lines.append(f"  市场: {fund.market.value}")
        lines.append(f"  基金公司: {fund.fund_company or '-'}")
        lines.append(f"  跟踪标的: {fund.tracking_index or '-'}")
        lines.append(f"  成立日期: {fund.inception_date or '-'}")
        lines.append(f"  上市日期: {fund.listing_date or '-'}")
        lines.append("")
        lines.append("[bold]费用信息[/bold]")
        lines.append(
            f"  管理费: {fund.management_fee * 100:.4f}% ({fund.management_fee})"
            if fund.management_fee
            else "  管理费: -"
        )
        lines.append(
            f"  托管费: {fund.custody_fee * 100:.4f}% ({fund.custody_fee})" if fund.custody_fee else "  托管费: -"
        )
        lines.append("")
        lines.append("[bold]规模数据[/bold]")
        lines.append(f"  当前规模: {fund.scale:.2f} 亿元" if fund.scale else "  当前规模: -")
        lines.append(f"  份额: {fund.share:.2f} 亿份" if fund.share else "  份额: -")
        lines.append(f"  单位净值: {fund.nav:.4f}" if fund.nav else "  单位净值: -")
        lines.append(f"  数据日期: {fund.scale_date or '-'}")

        if fund.scale_history:
            lines.append("")
            lines.append(f"[bold]规模历史 (最近 {len(fund.scale_history)} 期)[/bold]")
            history_table = Table(box=box.SIMPLE, show_header=True)
            history_table.add_column("日期", justify="center")
            history_table.add_column("规模(亿)", justify="right")
            history_table.add_column("份额(亿)", justify="right")
            history_table.add_column("净值", justify="right")
            for scale in fund.scale_history[:12]:
                history_table.add_row(
                    str(scale.report_date),
                    f"{scale.scale:.2f}" if scale.scale else "-",
                    f"{scale.share:.2f}" if scale.share else "-",
                    f"{scale.nav:.4f}" if scale.nav else "-",
                )
            lines.append(history_table)

        console.print(Panel("\n".join(str(x) for x in lines), border_style="cyan"))


class ForexPresenter(BasePresenter):
    @staticmethod
    def print_exchange_rate(rate: ExchangeRate):
        from .currency import get_currency_name

        cn_name = get_currency_name(rate.quote_currency)
        console.print(
            Panel(
                f"[bold]{rate.base_currency}/{rate.quote_currency}[/bold] ({cn_name}): [cyan]{rate.rate:.4f}[/cyan]\n"
                f"数据源: {rate.source or 'N/A'}",
                title="汇率查询结果",
                border_style="cyan",
            )
        )

    @staticmethod
    def print_exchange_rates(rates: list[ExchangeRate], base: str):
        from .currency import get_currency_name

        table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            title=f"{base} 汇率表",
        )
        table.add_column("货币对", justify="left", style="green")
        table.add_column("货币", justify="left", style="dim")
        table.add_column("汇率", justify="right", style="bold")

        for rate in rates:
            cn_name = get_currency_name(rate.quote_currency)
            table.add_row(
                f"{rate.base_currency}/{rate.quote_currency}",
                cn_name,
                f"{rate.rate:.4f}",
            )
        console.print(table)
