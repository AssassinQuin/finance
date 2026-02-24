import typer
from typing import List
from ...core.models import Asset, Market, AssetType
from ...core.storage import storage
from ...utils.presenter import ConsolePresenter

app = typer.Typer()

@app.command(name="add")
def add(codes: List[str]):
    """Add assets by code."""
    for code in codes:
        # Dummy logic: assumes stock, tries to guess market.
        market = Market.CN if code.isdigit() else Market.US
        asset = Asset(code=code, name=code, market=market, type=AssetType.STOCK)
        storage.add(asset)
    ConsolePresenter.print_success(f"Added {len(codes)} assets.")

@app.command(name="list")
def list_assets():
    """List all assets."""
    assets = storage.load()
    ConsolePresenter.print_asset_table(assets)

@app.command(name="remove")
def remove(code: str):
    """Remove asset."""
    if storage.remove(code):
        ConsolePresenter.print_success(f"Removed {code}")
    else:
        ConsolePresenter.print_error(f"Asset {code} not found")
