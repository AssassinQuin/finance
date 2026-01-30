import typer

from .commands import asset, gold, gpr, index, quote, search

app = typer.Typer(
    help="FCLI - 命令行金融信息工具",
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)

# --- 资产管理命令 ---
app.command(name="add", help="添加自选资产 (支持批量)", rich_help_panel="资产管理")(
    asset.add
)
app.command(
    name="list",
    help="列出所有自选资产 [bold][别名: ls][/bold]",
    rich_help_panel="资产管理",
)(asset.list_assets)
app.command(name="ls", help="列出资产 (list 简写)", hidden=True)(asset.list_assets)
app.command(
    name="remove",
    help="删除自选资产 [bold][别名: rm][/bold]",
    rich_help_panel="资产管理",
)(asset.remove)
app.command(name="rm", help="删除资产 (remove 简写)", hidden=True)(asset.remove)

# --- 行情与数据命令 ---
app.command(name="quote", help="获取实时行情 (默认命令)", rich_help_panel="行情与数据")(
    quote.quote
)
app.command(
    name="search", help="搜索全球资产 (股票/基金/指数)", rich_help_panel="行情与数据"
)(search.search)
app.command(
    name="gold",
    help="查看全球央行黄金储备及供需分析 [bold][别名: au][/bold]",
    rich_help_panel="行情与数据",
)(gold.gold)
app.command(name="au", help="黄金储备 (gold 简写)", hidden=True)(gold.gold)
app.command(name="gpr", help="全球地缘政治风险指数分析", rich_help_panel="行情与数据")(gpr.gpr)

# --- 系统管理命令 ---
app.command(name="update", help="更新本地资产索引数据库", rich_help_panel="系统管理")(
    index.update
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    FCLI - 命令行金融信息工具

    直接运行 'python run.py' 将默认展示实时行情。
    """
    if ctx.invoked_subcommand is None:
        quote.quote()


if __name__ == "__main__":
    app()
