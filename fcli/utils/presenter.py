from typing import List

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import plotext as plt

from ..core.models import Asset, Quote, ExchangeRate

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

        sorted_quotes = sorted(quotes, key=lambda q: q.change_percent, reverse=True)

        for quote in sorted_quotes:
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

        # 2. Reserves Table
        reserves_table = Table(
            box=box.SIMPLE,
            header_style="bold yellow",
            title="全球 Top 20 央行黄金储备 (多时间段变化)",
        )
        reserves_table.add_column("排名", justify="center", style="dim", width=4)
        reserves_table.add_column("国家/组织", justify="left", width=16)
        reserves_table.add_column("储备量(吨)", justify="right", style="bold", width=12)
        reserves_table.add_column("1月变化", justify="right", width=10)
        reserves_table.add_column("3月变化", justify="right", width=10)
        reserves_table.add_column("6月变化", justify="right", width=10)
        reserves_table.add_column("12月变化", justify="right", width=10)
        reserves_table.add_column("数据日期", justify="center", style="dim", width=8)

        def format_change(val):
            """Format change value with color."""
            if val is None or val == 0:
                return "-"
            if val > 0:
                return f"[bold red]+{val:.1f}[/bold red]"
            return f"[bold green]{val:.1f}[/bold green]"
            if val is None or val == 0:
                return "-"
            if val > 0:
                return f"[bold red]+{val:.1f}[/bold red]"
            return f"[bold green]{val:.1f}[/bold green]"
        
        # Add rows to the reserves table
        reserves = data.get("reserves", [])
        for i, r in enumerate(reserves, 1):
            reserves_table.add_row(
                str(i),
                r.get("country", ""),
                f"{r.get('amount', 0):.1f}",
                format_change(r.get("change_1m")),
                format_change(r.get("change_3m")),
                format_change(r.get("change_6m")),
                format_change(r.get("change_12m")),
                r.get("date", ""),
            )

        console.print(reserves_table)

        # 2. Global Supply/Demand Balance
        balance = data.get("balance", {})
        if balance:
            balance_table = Table(
                box=box.SIMPLE,
                header_style="bold cyan",
                title=f"全球黄金供需平衡表 ({balance.get('date', 'N/A')})",
            )
            balance_table.add_column("项目", justify="left")
            balance_table.add_column("供应 (吨)", justify="right", style="green")
            balance_table.add_column("项目", justify="left")
            balance_table.add_column("需求 (吨)", justify="right", style="red")

            supply = balance.get("supply", {})
            demand = balance.get("demand", {})

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
                    demand.get("investment"),
                ),
                ("", None, "央行净购入", demand.get("central_banks")),
                ("总供应", supply.get("total"), "总需求", demand.get("total")),
            ]

            for s_name, s_val, d_name, d_val in rows:
                s_val_str = f"{s_val:.1f}" if s_val is not None else ""
                d_val_str = f"{d_val:.1f}" if d_val is not None else ""
                balance_table.add_row(s_name, s_val_str, d_name, d_val_str)

            console.print(balance_table)

        if data.get("last_update"):
            console.print(f"\n[dim]最后更新时间: {data['last_update']}[/dim]")

    @staticmethod
    def print_gold_history(country_name: str, history: List[dict]):
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
    def print_gpr_chart(history: List[dict]):
        if not history:
            return

        dates = [h["date"] for h in history]
        values = [h["value"] for h in history]

        plt.clf()
        # Set date form to match YYYY-MM
        # Use single % because this is literal python string
        plt.date_form("Y-m")  # plotext uses Y-m instead of %Y-%m in some versions? No, let's try standard
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
    def status(message: str):
        return console.status(f"[bold green]{message}[/bold green]")

    @staticmethod
    def print_exchange_rate(rate: ExchangeRate):
        console.print(
            Panel(
                f"[bold]{rate.base_currency}/{rate.quote_currency}[/bold]: [cyan]{rate.rate:.4f}[/cyan]\n"
                f"数据源: {rate.source or 'N/A'}",
                title="汇率查询结果",
                border_style="cyan",
            )
        )

    @staticmethod
    def print_exchange_rates(rates: List[ExchangeRate], base: str):
        table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            title=f"{base} 汇率表",
        )
        table.add_column("货币对", justify="left", style="green")
        table.add_column("汇率", justify="right", style="bold")

        table.add_row(
            f"{rate.base_currency}/{rate.quote_currency}",
            f"{rate.rate:.4f}",
        )
        console.print(table)

    @staticmethod
    def print_gold_report_v2(data: dict):
        """
        优化版黄金报告 - 左右分栏布局
        左侧: Top 10 央行黄金储备
        右侧: SPDR持仓 + 供需平衡
        """
        if not data:
            ConsolePresenter.print_error("暂无黄金储备数据。")
            return

        from rich.columns import Columns
        from rich.panel import Panel

        # === 左侧: 央行储备 Top 10 ===
        left_table = Table(
            box=box.SIMPLE,
            header_style="bold yellow",
            title="",
            show_header=True,
            padding=(0, 1),
        )
        left_table.add_column("#", justify="center", style="dim", width=2)
        left_table.add_column("国家", justify="left", width=8)
        left_table.add_column("储备(吨)", justify="right", style="bold", width=10)
        left_table.add_column("年变动", justify="right", width=8)

        reserves = data.get("reserves", [])[:10]  # 只显示 Top 10

        def fmt_change(val):
            if val is None:
                return "[dim]-[/dim]"
            if val > 0:
                return f"[red]+{val:.1f}[/red]"
            if val < 0:
                return f"[green]{val:.1f}[/green]"
            return "0.0"

        for i, r in enumerate(reserves, 1):
            left_table.add_row(
                str(i),
                r["country"][:4] if len(r["country"]) > 4 else r["country"],
                f"{r['amount']:.1f}",
                fmt_change(r.get("change_1y")),
            )

        left_panel = Panel(
            left_table,
            title="[bold yellow]央行黄金储备 Top 10[/bold yellow]",
            border_style="yellow",
            padding=(0, 1),
        )

        # === 右侧上半: SPDR持仓 ===
        spdr = data.get("spdr", {})
        latest = spdr.get("latest")

        spdr_table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            show_header=True,
            padding=(0, 1),
        )
        spdr_table.add_column("指标", justify="left", width=10)
        spdr_table.add_column("数值", justify="right", width=12)

        if latest:
            trend_icon = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}.get(spdr.get("trend"), "")
            spdr_table.add_row("当前持仓", f"[bold]{latest['holdings']:.2f}[/bold] 吨")
            spdr_table.add_row("日变化", fmt_change(spdr.get("change_1d")))
            spdr_table.add_row("周变化", fmt_change(spdr.get("change_7d")) + " " + trend_icon)
            spdr_table.add_row("月变化", fmt_change(spdr.get("change_30d")))
            spdr_table.add_row("总价值", f"${latest['value'] / 1e9:.1f}B")
        else:
            spdr_table.add_row("数据", "[dim]暂无[/dim]")

        spdr_panel = Panel(
            spdr_table,
            title="[bold cyan]SPDR Gold Trust (GLD)[/bold cyan]",
            border_style="cyan",
            padding=(0, 1),
        )

        # === 右侧下半: 供需平衡 ===
        balance = data.get("balance", {})

        balance_table = Table(
            box=box.SIMPLE,
            header_style="bold green",
            show_header=True,
            padding=(0, 1),
        )
        balance_table.add_column("供应", justify="left", width=8)
        balance_table.add_column("吨", justify="right", width=6)
        balance_table.add_column("需求", justify="left", width=8)
        balance_table.add_column("吨", justify="right", width=6)

        if balance:
            supply = balance.get("supply", {})
            demand = balance.get("demand", {})

            rows = [
                ("矿产", supply.get("mine_production"), "金饰", demand.get("jewelry")),
                ("回收", supply.get("recycling"), "科技", demand.get("technology")),
                ("套保", supply.get("net_hedging"), "投资", demand.get("investment")),
                ("", None, "央行", demand.get("central_banks")),
            ]

            for s_name, s_val, d_name, d_val in rows:
                s_str = f"{s_val:.0f}" if s_val else ""
                d_str = f"{d_val:.0f}" if d_val else ""
                balance_table.add_row(s_name, s_str, d_name, d_str)

            # 总计行
            balance_table.add_row(
                "[bold]总计[/bold]",
                f"[bold]{supply.get('total', 0):.0f}[/bold]",
                "[bold]总计[/bold]",
                f"[bold]{demand.get('total', 0):.0f}[/bold]",
            )

        balance_panel = Panel(
            balance_table,
            title=f"[bold green]供需平衡 ({balance.get('date', 'N/A')})[/bold green]",
            border_style="green",
            padding=(0, 1),
        )

        # === 组合显示 ===
        right_content = Columns([spdr_panel, balance_panel])

        from rich.console import Group

        console.print()
        console.print(Columns([left_panel, Group(spdr_panel, balance_panel)]))

        if data.get("last_update"):
            console.print(f"\n[dim]更新时间: {data['last_update']}[/dim]")
