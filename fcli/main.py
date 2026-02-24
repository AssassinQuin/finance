import typer
from .cli.commands import asset_app, quote_app, market_app, forex_app, search_app, system_app
from .cli.commands.quote import quote as quote_cmd

app = typer.Typer(
    help="FCLI - 命令行金融信息工具",
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.add_typer(asset_app, name="add", help="添加自选资产")
app.add_typer(asset_app, name="asset", help="资产管理", hidden=True)

app.command(name="list", help="列出所有自选资产 [bold][别名: ls][/bold]")(lambda: None)
app.command(name="ls", help="列出资产 (list 简写)", hidden=True)(lambda: None)
app.command(name="remove", help="删除自选资产 [bold][别名: rm][/bold]")(lambda: None)
app.command(name="rm", help="删除资产 (remove 简写)", hidden=True)(lambda: None)

app.command(name="quote", help="获取实时行情 (默认命令)")(quote_cmd)
app.command(name="search", help="搜索全球资产 (股票/基金/指数)")(lambda: None)

app.add_typer(market_app, name="market", help="市场数据 (gold, gpr)")
app.add_typer(forex_app, name="forex", help="汇率查询")
app.add_typer(system_app, name="system", help="系统管理")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    FCLI - 命令行金融信息工具

    直接运行 'fcli' 将默认展示实时行情。
    """
    if ctx.invoked_subcommand is None:
        quote_cmd()


if __name__ == "__main__":
    app()
