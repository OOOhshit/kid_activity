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

    # Deduplicate by (title, city, category) — same event, no matter the source page
    seen = set()
    unique = []
    for act in all_activities:
        key = (act["title"].lower().strip(), act["city"], act["category"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(act)

    insert_activities(unique)
    logger.info(
        f"Scraping complete. {len(all_activities)} raw, {len(unique)} unique activities inserted."
    )
    return len(unique)
