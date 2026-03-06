"""
Central bank scrapers module.
Provides direct scraping from central bank websites.
"""

import logging

from ..base import BaseScraper

logger = logging.getLogger(__name__)

# Import all central bank scrapers
from .fra_bdf import BanqueDeFranceScraper
from .jpn_boj import BOJScraper
from .usa_fred import FREDSscraper

# Registry of available central bank scrapers
CENTRAL_BANK_SCRAPERS: dict[str, type[BaseScraper]] = {
    "USA": FREDSscraper,
    "FRA": BanqueDeFranceScraper,
    "JPN": BOJScraper,
}


def get_scraper(country_code: str) -> BaseScraper:
    """
    Get scraper instance for a specific country.

    Args:
        country_code: ISO 3-letter country code

    Returns:
        BaseScraper instance or None if not available
    """
    scraper_class = CENTRAL_BANK_SCRAPERS.get(country_code.upper())
    if scraper_class:
        return scraper_class()
    return None


def get_supported_countries() -> list:
    """
    Get list of countries with direct scrapers.

    Returns:
        List of ISO country codes
    """
    return list(CENTRAL_BANK_SCRAPERS.keys())
