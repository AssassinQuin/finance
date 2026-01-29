import asyncio

import typer

from ..core.storage import storage
from ..providers.fetcher import fetcher
from ..services.gold_service import gold_service
from ..utils.presenter import ConsolePresenter

app = typer.Typer(help="查看全球黄金储备与供需关系")


@app.callback(invoke_without_command=True)
def gold(
    update: bool = typer.Option(False, "--update", "-u", help="强制从 API 更新数据"),
    detail: bool = typer.Option(False, "--detail", "-d", help="显示详细供需平衡表"),
    history: str = typer.Option(None, "--history", "-h", help="查看特定国家的历史趋势 (如 CN, US)")
):
    """
    查看全球主要央行黄金储备变动及供需平衡。
    """

    async def _do_gold():
        try:
            if update:
                with ConsolePresenter.status("正在从 IMF 和权威机构获取黄金数据..."):
                    count = await gold_service.update_gold_data()
                    ConsolePresenter.print_success(f"成功更新 {count} 条黄金储备记录。")

            if history:
                records = gold_service.get_history_report(history)
                if not records:
                    ConsolePresenter.print_warning(f"未找到 {history} 的数据，请尝试先运行 --update。")
                    return
                ConsolePresenter.print_gold_history(records[0]["country"], records)
                return

            report = gold_service.get_latest_report()
            if not report:
                ConsolePresenter.print_warning("本地暂无数据，请运行 'python run.py gold --update' 初始化。")
                return

            ConsolePresenter.print_gold_report(report)
        finally:
            await fetcher.close()

    asyncio.run(_do_gold())
