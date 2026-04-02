"""Scraper for MJC / community center activity pages.

Discovers agenda/events pages from the MJC website, then scrapes
each page for family and kids activities.
"""

import logging

from scraper.base import BaseScraper
from config import SCRAPER_SOURCES

logger = logging.getLogger(__name__)


class MJCScraper(BaseScraper):
    category = "mjc"

    async def scrape(self, city: str) -> list[dict]:
        url = SCRAPER_SOURCES.get("mjc", {}).get(city)
        if not url:
            return []

        activities = []
        try:
            # Step 1: Discover agenda/events pages from the site
            agenda_pages = await self.discover_agenda_pages(url)
            logger.info(f"MJC scraper for {city}: found {len(agenda_pages)} agenda page(s)")

            # Step 2: Scrape each discovered page for family/kids events
            for page_url in agenda_pages:
                try:
                    page_activities = await self.scrape_agenda_page(page_url, city)
                    activities.extend(page_activities)
                except Exception as e:
                    logger.warning(f"Failed to scrape MJC page {page_url}: {e}")

        except Exception as e:
            logger.error(f"MJC scraper failed for {city}: {e}")

        logger.info(f"MJC scraper for {city}: collected {len(activities)} activities")
        return activities
