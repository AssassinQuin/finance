"""
Gold reserve data scrapers.
Supports multiple data sources: WGC, IMF, and direct central bank scrapers.
"""

from .base import BaseScraper, ScraperResult
from .wgc_scraper import WGCScraper
from .imf_scraper import IMFScraper

__all__ = [
    "BaseScraper",
    "ScraperResult",
    "WGCScraper",
    "IMFScraper",
]
