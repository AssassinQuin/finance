import plotext as plt
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.config import config
from ..core.models import Asset, ExchangeRate, Fund, FundDetail, Quote

console = Console()

_display_cache: dict[str, dict[str, str]] | None = None


def _get_display_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    global _display_cache
    if _display_cache is None:
        d = config.display
        _display_cache = {
            "market": d.market_map if d.market_map else {},
            "type": d.type_map if d.type_map else {},
            "color": d.type_color if d.type_color else {},
        }
    return _display_cache["market"], _display_cache["type"], _display_cache["color"]


class ConsolePresenter:
    @staticmethod
    def _get_market_display(market_value: str) -> str:
        market_map, _, _ = _get_display_maps()
        return market_map.get(market_value, market_value)

    @staticmethod
    def _get_type_display(type_value: str) -> tuple[str, str]:
        _, type_map, type_color = _get_display_maps()
        type_cn = type_map.get(type_value, type_value)
        type_color = type_color.get(type_value, "white")
        return type_cn, type_color

    @staticmethod
    def _format_change(val: float | None) -> str:
        if val is None:
            return "-"
        rounded = round(val, 1)
        if rounded == 0:
            return "0.0"
        if rounded > 0:
            return f"[bold red]+{rounded:.1f}[/bold red]"
        return f"[bold green]{rounded:.1f}[/bold green]"

    @staticmethod
    def _format_change_compact(val: float | None) -> str:
        if val is None:
            return "[dim]-[/dim]"
        rounded = round(val, 1)
        if rounded == 0:
            return "0.0"
        if rounded > 0:
            return f"[red]+{rounded:.1f}[/red]"
        return f"[green]{rounded:.1f}[/green]"

    @staticmethod
    def print_asset_table(assets: list[Asset]):
        table = Table(box=box.SIMPLE, header_style="bold cyan")
        table.add_column("代码", justify="left", style="green")
        table.add_column("名称", justify="left")
        table.add_column("市场", justify="center")
        table.add_column("类型", justify="center")

        for asset in assets:
            market_cn = ConsolePresenter._get_market_display(asset.market.value)
            type_cn, type_color = ConsolePresenter._get_type_display(asset.type.value)

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

            market_cn = ConsolePresenter._get_market_display(quote.market.value)
            type_cn, type_color = ConsolePresenter._get_type_display(quote.type.value)

            table.add_row(
                str(i),
                quote.code,
                quote.name,
                f"{quote.price:.2f}",
                f"[{change_style}]{change_str}[/{change_style}]",
                quote.update_time.strftime("%Y-%m-%d %H:%M"),
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
            market_cn = ConsolePresenter._get_market_display(asset.market.value)
            type_cn, _ = ConsolePresenter._get_type_display(asset.type.value)

            table.add_row(asset.code, asset.name, market_cn, type_cn, asset.api_code)
        console.print(table)

    @staticmethod
    def print_gpr_report(gpr_data: dict):
        if not gpr_data:
            ConsolePresenter.print_error("暂无 GPR 数据。")
            return

        gpr_table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            title="全球地缘政治风险指数 (GPR) 多维分析",
        )
        gpr_table.add_column("维度", justify="center")
        gpr_table.add_column("历史值", justify="right")
        gpr_table.add_column("当前值", justify="right", style="bold")
        gpr_table.add_column("绝对变动", justify="right")
        gpr_table.add_column("幅度 (%)", justify="right")

        latest = gpr_data["latest"]
        risk = gpr_data["risk"]

        for label, info in gpr_data["horizons"].items():
            if info:
                change = info["change"]
                change_pct = info["change_pct"]
                style = "bold red" if change > 0 else ("bold green" if change < 0 else "white")

                gpr_table.add_row(
                    label,
                    f"{info['value']:.2f}",
                    f"{latest['value']:.2f}",
                    f"[{style}]{change:+.2f}[/{style}]",
                    f"[{style}]{change_pct:+.2f}%[/{style}]",
                )

        console.print(
            Panel(
                f"当前 GPR 指数: [bold]{latest['value']:.2f}[/bold] ({latest['date']})\n风险等级: [{risk['color']}]{risk['level']}[/{risk['color']}]",
                title="[bold yellow]地缘风险概览[/bold yellow]",
                border_style="yellow",
            )
        )
        console.print(gpr_table)

    @staticmethod
    def print_gold_report(data: dict):
        if not data:
            ConsolePresenter.print_error("暂无黄金储备数据。")
            return

        reserves_table = Table(
            box=box.SIMPLE,
            header_style="bold yellow",
            title="全球 Top 20 央行黄金储备",
        )
        reserves_table.add_column("排名", justify="center", style="dim", width=4)
        reserves_table.add_column("国家/组织", justify="left", width=16)
        reserves_table.add_column("储备量(吨)", justify="right", style="bold", width=12)
        reserves_table.add_column("同比", justify="right", width=10)
        reserves_table.add_column("年初至今", justify="right", width=10)
        reserves_table.add_column("月趋势(吨)", justify="right", width=10)
        reserves_table.add_column("R²", justify="right", width=6)
        reserves_table.add_column("数据日期", justify="center", style="dim", width=8)

        reserves = data.get("reserves", [])
        for i, r in enumerate(reserves, 1):
            trend_r2 = r.get("trend_r2")
            trend_r2_str = f"{trend_r2:.2f}" if trend_r2 is not None else "-"
            reserves_table.add_row(
                str(i),
                r.get("country", ""),
                f"{r.get('amount', 0):.1f}",
                ConsolePresenter._format_change(r.get("yoy_change")),
                ConsolePresenter._format_change(r.get("ytd_change")),
                ConsolePresenter._format_change(r.get("monthly_trend")),
                trend_r2_str,
                r.get("date", ""),
            )

        console.print(reserves_table)

        balance = data.get("balance", {})
        if balance:
            balance_table = ConsolePresenter._build_supply_demand_table(balance)
            console.print(balance_table)

        if data.get("last_update"):
            console.print(f"\n[dim]最后更新时间: {data['last_update']}[/dim]")

    @staticmethod
    def _build_supply_demand_table(balance: dict) -> Table:
        supply = balance.get("supply", {})
        demand = balance.get("demand", {})

        table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            title=f"全球黄金供需平衡表 ({balance.get('period', 'N/A')})",
        )
        table.add_column("项目", justify="left")
        table.add_column("供应 (吨)", justify="right", style="green")
        table.add_column("项目", justify="left")
        table.add_column("需求 (吨)", justify="right", style="red")

        rows = [
            (
                "矿产金",
                supply.get("mine_production"),
                "金饰需求",
                demand.get("jewelry"),
            ),
            (
                "回收金",
                supply.get("recycling"),
                "科技工业",
                demand.get("technology"),
            ),
            (
                "净套期保值",
                supply.get("net_hedging"),
                "投资需求",
                demand.get("investment", {}).get("total"),
            ),
            ("", None, "央行净购入", demand.get("central_banks")),
            ("总供应", supply.get("total"), "总需求", demand.get("total")),
        ]

        for s_name, s_val, d_name, d_val in rows:
            s_val_str = f"{s_val:.1f}" if s_val is not None else ""
            d_val_str = f"{d_val:.1f}" if d_val is not None else ""
            table.add_row(s_name, s_val_str, d_name, d_val_str)

        return table

    @staticmethod
    def print_gold_supply_balance(balance: dict):
        if not balance:
            ConsolePresenter.print_warning("暂无黄金供需数据")
            return

        balance_table = ConsolePresenter._build_supply_demand_table(balance)
        console.print(Panel(balance_table, title="[bold yellow]黄金供需数据[/bold yellow]", border_style="yellow"))

    @staticmethod
    def print_gold_history(country_name: str, history: list[dict]):
        if not history:
            ConsolePresenter.print_error(f"未找到 {country_name} 的历史数据。")
            return

        table = Table(
            box=box.SIMPLE,
            header_style="bold magenta",
            title=f"{country_name} 过去 12 个月黄金储备趋势",
        )
        table.add_column("日期", justify="center")
        table.add_column("储备量 (吨)", justify="right", style="bold")
        table.add_column("环比变动", justify="right")

        for i in range(len(history)):
            curr = history[i]
            change_str = "-"
            change_style = "white"

            if i < len(history) - 1:
                prev = history[i + 1]
                diff = curr["amount"] - prev["amount"]
                change_str = f"{diff:+.2f}"
                change_style = "bold red" if diff > 0 else ("bold green" if diff < 0 else "white")

            table.add_row(
                curr["date"],
                f"{curr['amount']:.2f}",
                f"[{change_style}]{change_str}[/{change_style}]",
            )
        console.print(table)

    @staticmethod
    def print_gold_trend_chart(trend_data: dict[str, list[dict]]) -> None:
        if not trend_data or all(not v for v in trend_data.values()):
            return

        plt.clf()
        plt.theme("dark")
        plt.plotsize(100, 25)
        plt.date_form("Y-m")

        colors = ["yellow", "red", "cyan", "green", "magenta"]
        legend_items = []

        for i, (country_code, data_points) in enumerate(trend_data.items()):
            if not data_points:
                continue
            color = colors[i % len(colors)]
            dates = [dp["date"] for dp in data_points]
            amounts = [dp["amount"] for dp in data_points]
            country_name = data_points[0].get("country_name", country_code) if data_points else country_code
            plt.plot(dates, amounts, color=color)
            legend_items.append(f"[{color}]●[/{color}] {country_name}")

        plt.title("全球 Top 5 央行黄金储备趋势 (3年)")
        plt.xlabel("日期")
        plt.ylabel("储备量 (吨)")
        plt.show()

        if legend_items:
            console.print("  " + "  ".join(legend_items))

    @staticmethod
    def print_gpr_chart(history: list[dict]):
        if not history:
            return

        dates = [h["date"] for h in history]
        values = [h["value"] for h in history]

        plt.clf()
        plt.date_form("Y-m")
        plt.plot(dates, values, marker="dot", color="cyan")
        plt.title("地缘政治风险指数 (GPR) 历史趋势")
        plt.xlabel("日期")
        plt.ylabel("指数值")
        plt.theme("dark")
        plt.plotsize(100, 30)
        plt.show()

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
    def print_info(message: str):
        console.print(f"[dim]{message}[/dim]")

    @staticmethod
    def status(message: str):
        return console.status(f"[bold green]{message}[/bold green]")

    @staticmethod
    def print_exchange_rate(rate: ExchangeRate):
        from ..services.forex_service import get_currency_name

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
        from ..services.forex_service import get_currency_name

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
        lines.append(f"[bold]基本信息[/bold]")
        lines.append(f"  基金类型: {type_label}")
        lines.append(f"  投资类型: {fund.invest_type.value if fund.invest_type else '-'}")
        lines.append(f"  市场: {fund.market.value}")
        lines.append(f"  基金公司: {fund.fund_company or '-'}")
        lines.append(f"  跟踪标的: {fund.tracking_index or '-'}")
        lines.append(f"  成立日期: {fund.inception_date or '-'}")
        lines.append(f"  上市日期: {fund.listing_date or '-'}")
        lines.append("")
        lines.append(f"[bold]费用信息[/bold]")
        lines.append(
            f"  管理费: {fund.management_fee * 100:.4f}% ({fund.management_fee})"
            if fund.management_fee
            else "  管理费: -"
        )
        lines.append(
            f"  托管费: {fund.custody_fee * 100:.4f}% ({fund.custody_fee})" if fund.custody_fee else "  托管费: -"
        )
        lines.append("")
        lines.append(f"[bold]规模数据[/bold]")
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
