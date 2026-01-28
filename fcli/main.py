import typer

from .commands import asset, index, quote, search

app = typer.Typer(help="FCLI - 命令行金融信息工具")

# Register commands
# 1. Asset commands: add, remove, list
app.add_typer(
    asset.app, name="asset", hidden=True
)  # Hack to expose subcommands directly? No.

# We want commands to be top-level:
# python run.py add ...
# python run.py quote ...

# So we register the functions directly or use sub-typers if we wanted groups.
# But current design is flat.
# Typer doesn't easily support merging multiple Typers into the root unless we register callbacks.

# Let's redefine the root app here and import commands.
# Actually, the cleaner way is to keep asset.app as a sub-app or register its commands to root.
# But we defined asset.app as a Typer().

# Strategy:
# 1. Use command groups? No, user wants `run.py add`.
# 2. Register imported functions.

app.command(name="add", help="添加资产")(asset.add)
app.command(name="remove", help="删除资产")(asset.remove)
app.command(name="rm", help="删除资产 (remove 简写)", hidden=True)(asset.remove)
app.command(name="list", help="列出资产")(asset.list_assets)
app.command(name="ls", help="列出资产 (list 简写)", hidden=True)(asset.list_assets)

app.command(name="quote", help="获取行情")(quote.quote)
app.command(name="search", help="搜索资产")(search.search)
app.command(name="update", help="更新本地索引")(index.update)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    FCLI - 命令行金融信息工具
    
    默认行为: 如果不输入任何子命令，将直接运行 'quote' 获取行情。
    """
    if ctx.invoked_subcommand is None:
        quote.quote()


if __name__ == "__main__":
    app()
