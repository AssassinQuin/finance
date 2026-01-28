import asyncio
from collections import defaultdict
from typing import List

from ..core.models import Asset, Quote
from ..sources.base import QuoteSource
from ..sources.factory import SourceFactory


class QuoteService:
    async def get_quotes(self, assets: List[Asset]) -> List[Quote]:
        """
        Fetch quotes for a list of assets, using the appropriate source strategy for each.
        """
        # Group assets by source strategy
        source_groups: defaultdict[QuoteSource, List[Asset]] = defaultdict(list)

        for asset in assets:
            source = SourceFactory.get_source(asset)
            source_groups[source].append(asset)

        # Create tasks for each source
        tasks = []
        for source, group_assets in source_groups.items():
            tasks.append(source.fetch(group_assets))

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Flatten results
        quotes = []
        for res in results:
            quotes.extend(res)

        # Sort by change_percent descending (as per user preference)
        quotes.sort(key=lambda x: x.change_percent, reverse=True)

        return quotes


quote_service = QuoteService()
