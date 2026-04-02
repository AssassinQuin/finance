from typing import Annotated

import typer

from ..core.container import container
from ..core.models.gpr import GPRIndexType
from ..utils.command import run_command
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="地缘政治风险指数", context_settings={"help_option_names": ["-h", "--help"]})

VALID_INDEX_TYPES = [it.value for it in GPRIndexType]


@app.callback(invoke_without_command=True)
def index(
    update: Annotated[bool, typer.Option("-u", "--update", help="强制更新数据")] = False,
    full: Annotated[bool, typer.Option("-f", "--full", help="全量更新（含多国数据）")] = False,
    chart: Annotated[bool, typer.Option("--chart/--no-chart", help="显示图表")] = True,
    country: Annotated[
        str,
        typer.Option("-c", "--country", help="国家代码 (如 CHN, USA, WLD)"),
    ] = "WLD",
    index_type: Annotated[
        str,
        typer.Option("-t", "--index-type", help="指数类型"),
    ] = "GPR",
):
    """地缘政治风险指数 (默认命令)

    显示 GPR 指数分析报告和历史趋势图。

    示例:
        fcli gpr                       # 全球 GPR 总指数
        fcli gpr -c CHN                # 中国 GPR
        fcli gpr -t GPRT               # GPR 威胁指数
        fcli gpr -c USA -t GPRA        # 美国 GPR 行为指数
        fcli gpr -u                    # 强制更新数据
        fcli gpr -u -f                 # 全量更新（含 44 国数据）
        fcli gpr --no-chart            # 不显示图表
    """
    if index_type not in VALID_INDEX_TYPES:
        ConsolePresenter.print_error(f"无效指数类型: {index_type}，可选: {', '.join(VALID_INDEX_TYPES)}")
        return
    run_command(_index(update, full, chart, country, index_type), "获取 GPR 数据失败")


async def _index(update: bool, full: bool, chart: bool, country: str, index_type: str) -> None:
    async with container.session():
        if update:
            with ConsolePresenter.status("更新 GPR 数据..."):
                result = await container.gpr_service.update_data(full=full)
            if result.get("success"):
                ConsolePresenter.print_success(f"已更新 GPR 数据：{result.get('records', 0)} 条记录")
            else:
                ConsolePresenter.print_error(f"更新失败：{result.get('error', 'Unknown error')}")
                return

        with ConsolePresenter.status("获取 GPR 分析报告..."):
            analysis = await container.gpr_service.get_gpr_analysis(
                country_code=country,
                index_type=index_type,
            )
        if not analysis:
            if country != "WLD" and index_type != "GPR":
                ConsolePresenter.print_warning(
                    f"国别数据 ({country}) 仅支持 GPR 总指数，不支持子指数 ({index_type})。"
                    f"\n子指数 (GPRT/GPRA/GPRH) 仅提供全球数据，请使用 -c WLD -t {index_type}"
                )
            else:
                ConsolePresenter.print_warning("暂无 GPR 数据，请使用 -u 更新")
            return

        ConsolePresenter.print_gpr_report(analysis)

        if chart:
            with ConsolePresenter.status("获取历史数据..."):
                history = await container.gpr_service.get_gpr_history(
                    months=120,
                    country_code=country,
                    index_type=index_type,
                )
            ConsolePresenter.print_gpr_chart(history, country_code=country, index_type=index_type)


@app.command()
def history(
    months: Annotated[int, typer.Option("-m", "--months", help="显示月数")] = 120,
    country: Annotated[
        str,
        typer.Option("-c", "--country", help="国家代码 (如 CHN, USA, WLD)"),
    ] = "WLD",
    index_type: Annotated[
        str,
        typer.Option("-t", "--index-type", help="指数类型"),
    ] = "GPR",
):
    """GPR 历史趋势

    示例:
        fcli gpr history
        fcli gpr history -m 60
        fcli gpr history -c CHN
        fcli gpr history -c USA -t GPRT
    """
    if index_type not in VALID_INDEX_TYPES:
        ConsolePresenter.print_error(f"无效指数类型: {index_type}，可选: {', '.join(VALID_INDEX_TYPES)}")
        return
    run_command(_history(months, country, index_type), "获取历史数据失败")


async def _history(months: int, country: str, index_type: str) -> None:
    async with container.session():
        with ConsolePresenter.status("获取历史数据..."):
            data = await container.gpr_service.get_gpr_history(
                months=months,
                country_code=country,
                index_type=index_type,
            )
        if data:
            ConsolePresenter.print_gpr_chart(data, country_code=country, index_type=index_type)
        else:
            ConsolePresenter.print_warning("暂无历史数据")


@app.command()
def compare(
    countries: Annotated[
        str | None,
        typer.Argument(help="国家代码，逗号分隔 (如 CHN,USA,RUS)"),
    ] = None,
):
    """GPR 多国对比排名

    示例:
        fcli gpr compare                    # 默认主要国家
        fcli gpr compare CHN,USA,RUS,UKR    # 指定国家
        fcli gpr compare CHN,USA,JPN,DEU,GBR
    """
    country_list = None
    if countries:
        country_list = [c.strip().upper() for c in countries.split(",") if c.strip()]
    run_command(_compare(country_list), "获取多国对比数据失败")


async def _compare(country_codes: list[str] | None) -> None:
    async with container.session():
        if country_codes is None:
            country_codes = ["CHN", "USA", "RUS", "UKR", "DEU", "GBR", "JPN", "IND", "ISR", "TUR"]

        with ConsolePresenter.status("获取多国 GPR 对比..."):
            comparison = await container.gpr_service.get_multi_country_comparison(
                country_codes=country_codes,
            )
        if comparison:
            ConsolePresenter.print_country_comparison(comparison)
        else:
            ConsolePresenter.print_warning("暂无多国对比数据，请先使用 fcli gpr -u -f 全量更新")
