import typer
import asyncio
from typing import List
from ...core.storage import storage
from ...core.models import Quote, AssetType, Market
from ...infra.http_client import http_client
from ...utils.presenter import ConsolePresenter
from ...services.quote_service import quote_service

app = typer.Typer()

async def fetch_quotes():
    assets = storage.load()
    if not assets:
        ConsolePresenter.print_warning("No assets to quote. Use 'add' to add assets.")
        return

    quotes = await quote_service.fetch_all(assets)
    
    if not quotes:
        ConsolePresenter.print_warning("Failed to fetch quotes.")
        return
    
    ConsolePresenter.print_quote_table(quotes)
    
    await http_client.close()

@app.callback(invoke_without_command=True)
def quote():
    """Get quotes."""
    asyncio.run(fetch_quotes())
