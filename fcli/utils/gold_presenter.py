import plotext as plt
from rich import box
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

from ..core.models.gpr import GPR_COUNTRY_NAMES, GPRIndexType
from .base_presenter import BasePresenter, console


class GoldPresenter(BasePresenter):
    @staticmethod
    def print_gpr_report(gpr_data: dict):
        if not gpr_data:
            GoldPresenter.print_error("暂无 GPR 数据。")
            return

        country_code = gpr_data.get("country_code", "WLD")
        index_type = gpr_data.get("index_type", "GPR")
        country_name = GPR_COUNTRY_NAMES.get(country_code, country_code)
        index_display = "GPR"
        for it in GPRIndexType:
            if it.value == index_type:
                index_display = it.display_name
                break

        title = f"{country_name} {index_display} 多维分析"

        gpr_table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            title=title,
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

        overview_text = (
            f"当前指数: [bold]{latest['value']:.2f}[/bold] ({latest['date']})\n"
            f"风险等级: [{risk['color']}]{risk['level']}[/{risk['color']}]"
        )

        stats = gpr_data.get("stats")
        if stats:
            stats_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            stats_table.add_column("指标", style="dim")
            stats_table.add_column("值", justify="right", style="bold")
            stats_table.add_row("均值", f"{stats['mean']:.2f}")
            stats_table.add_row("中位数", f"{stats['median']:.2f}")
            stats_table.add_row("最小值", f"{stats['min']:.2f}")
            stats_table.add_row("最大值", f"{stats['max']:.2f}")
            stats_table.add_row("75%分位", f"{stats['percentile_75']:.2f}")
            console.print(
                Columns(
                    [
                        Panel(overview_text, title="[bold yellow]地缘风险概览[/bold yellow]", border_style="yellow"),
                        Panel(stats_table, title="[bold cyan]统计指标[/bold cyan]", border_style="cyan"),
                    ]
                )
            )
        else:
            console.print(
                Panel(
                    overview_text,
                    title="[bold yellow]地缘风险概览[/bold yellow]",
                    border_style="yellow",
                )
            )
        console.print(gpr_table)

    @staticmethod
    def print_gold_report(data: dict):
        if not data:
            GoldPresenter.print_error("暂无黄金储备数据。")
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
                GoldPresenter._format_change(r.get("yoy_change")),
                GoldPresenter._format_change(r.get("ytd_change")),
                GoldPresenter._format_change(r.get("monthly_trend")),
                trend_r2_str,
                r.get("date", ""),
            )

        console.print(reserves_table)

        balance = data.get("balance", {})
        if balance:
            balance_table = GoldPresenter._build_supply_demand_table(balance)
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
            GoldPresenter.print_warning("暂无黄金供需数据")
            return

        balance_table = GoldPresenter._build_supply_demand_table(balance)
        console.print(Panel(balance_table, title="[bold yellow]黄金供需数据[/bold yellow]", border_style="yellow"))

    @staticmethod
    def print_gold_history(country_name: str, history: list[dict]):
        if not history:
            GoldPresenter.print_error(f"未找到 {country_name} 的历史数据。")
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
    def print_gpr_chart(
        history: list[dict],
        country_code: str = "WLD",
        index_type: str = "GPR",
    ):
        if not history:
            return

        country_name = GPR_COUNTRY_NAMES.get(country_code, country_code)
        index_display = index_type
        for it in GPRIndexType:
            if it.value == index_type:
                index_display = it.display_name
                break

        dates = [h["date"] for h in history]
        values = [h["value"] for h in history]

        plt.clf()
        plt.date_form("Y-m")
        plt.plot(dates, values, color="cyan")

        if len(values) >= 12:
            ma12 = GoldPresenter._moving_average(values, 12)
            plt.plot(dates, ma12, color="yellow")

        if len(values) >= 24:
            ma24 = GoldPresenter._moving_average(values, 24)
            plt.plot(dates, ma24, color="red")

        plt.title(f"{country_name} {index_display} 历史趋势")
        plt.xlabel("日期")
        plt.ylabel("指数值")
        plt.theme("dark")
        plt.plotsize(100, 30)
        plt.show()

        legend_parts = ["[cyan]●[/cyan] 实际值"]
        if len(values) >= 12:
            legend_parts.append("[yellow]●[/yellow] MA12")
        if len(values) >= 24:
            legend_parts.append("[red]●[/red] MA24")
        console.print("  " + "  ".join(legend_parts))

    @staticmethod
    def print_country_comparison(comparison: list[dict]):
        if not comparison:
            GoldPresenter.print_warning("暂无多国对比数据")
            return

        table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            title="GPR 多国对比排名",
        )
        table.add_column("排名", justify="center", style="dim", width=4)
        table.add_column("国家", justify="left", width=12)
        table.add_column("GPR 指数", justify="right", style="bold", width=12)
        table.add_column("日期", justify="center", style="dim", width=8)
        table.add_column("风险等级", justify="center", width=16)

        for i, item in enumerate(comparison, 1):
            val = item["gpr_index"]
            if val > 150:
                risk_text = "[bold red]高风险[/bold red]"
            elif val > 100:
                risk_text = "[yellow]中等[/yellow]"
            else:
                risk_text = "[green]正常[/green]"

            table.add_row(
                str(i),
                item.get("country_name", item["country_code"]),
                f"{val:.2f}",
                item.get("report_date", "-"),
                risk_text,
            )

        console.print(table)

    @staticmethod
    def _moving_average(data: list[float], window: int) -> list[float | None]:
        result: list[float | None] = []
        for i in range(len(data)):
            if i < window - 1:
                result.append(None)
            else:
                subset = data[i - window + 1 : i + 1]
                result.append(sum(subset) / window)
        return result
