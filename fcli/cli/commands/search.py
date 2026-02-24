import typer
from ...utils.presenter import ConsolePresenter

app = typer.Typer()

@app.callback(invoke_without_command=True)
def search(keyword: str):
    """Search assets."""
    ConsolePresenter.print_warning("Search service temporarily unavailable.")
