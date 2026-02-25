"""
Gold reserve data scrapers.
Supports multiple data sources: WGC, IMF, AkShare, SAFE, and direct central bank scrapers.
"""

from .base import BaseScraper, ScraperResult
from .wgc_scraper import WGCScraper
from .imf_scraper import IMFScraper
from .akshare_scraper import AkShareScraper
from .safe_scraper import SAFEScraper

__all__ = [
    "BaseScraper",
    "ScraperResult",
    "WGCScraper",
    "IMFScraper",
    "AkShareScraper",
    "SAFEScraper",
]
