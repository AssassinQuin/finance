from .watchlist_service import watchlist_service

# Create global quote service instance
from fcli.core.container import container

quote_service = container.quote_service
