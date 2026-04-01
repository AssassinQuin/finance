"""
Gold reserve data scrapers.
Primary sources: IMF SDMX 3.0 API, World Gold Council
"""

from .base import BaseScraper, ScraperResult
from .imf_scraper import IMFScraper
from .wgc_scraper import WGCScraper

__all__ = [
    "BaseScraper",
    "ScraperResult",
    "IMFScraper",
    "WGCScraper",
]
