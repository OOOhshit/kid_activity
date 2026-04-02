"""Orchestrates all scrapers across all cities."""

import logging

from config import CITIES
from db import insert_activities
from scraper.library import LibraryScraper
from scraper.mjc import MJCScraper
from scraper.theatre import TheatreScraper

logger = logging.getLogger(__name__)


async def run_all_scrapers():
    """Run all category scrapers for all configured cities."""
    scrapers = [
        LibraryScraper(),
        MJCScraper(),
        TheatreScraper(),
    ]

    all_activities = []
    for scraper in scrapers:
        for city in CITIES:
            try:
                logger.info(f"Scraping {scraper.category} in {city}...")
                results = await scraper.scrape(city)
                all_activities.extend(results)
                logger.info(f"  Found {len(results)} activities")
            except Exception as e:
                logger.error(
                    f"Scraper {scraper.category}/{city} failed: {e}"
                )

    insert_activities(all_activities)
    logger.info(f"Scraping complete. Total activities collected: {len(all_activities)}")
    return len(all_activities)
