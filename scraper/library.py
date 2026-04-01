"""Scraper for municipal library event pages."""

import logging

from scraper.base import BaseScraper
from config import SCRAPER_SOURCES

logger = logging.getLogger(__name__)


class LibraryScraper(BaseScraper):
    category = "library"

    async def scrape(self, city: str) -> list[dict]:
        url = SCRAPER_SOURCES.get("library", {}).get(city)
        if not url:
            return []

        activities = []
        try:
            soup = await self.fetch_page(url)

            # Common patterns for library agenda pages
            # Look for event items in common CSS patterns
            selectors = [
                "article.event", ".agenda-item", ".event-item",
                ".views-row", ".node--type-event", "li.event",
                ".agenda-list article", ".field-content",
            ]

            items = []
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    break

            if not items:
                # Fallback: look for any structured content with dates
                items = soup.find_all(["article", "div"], class_=lambda c: c and (
                    "event" in str(c).lower() or "agenda" in str(c).lower()
                ))

            for item in items:
                title_el = item.find(["h2", "h3", "h4", "a"])
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title:
                    continue

                # Extract link
                link_el = item.find("a", href=True)
                link = link_el["href"] if link_el else None
                if link and not link.startswith("http"):
                    # Make absolute URL
                    from urllib.parse import urljoin
                    link = urljoin(url, link)

                # Extract date, time, price from surrounding text
                full_text = item.get_text(" ", strip=True)
                event_date = self.parse_french_date(full_text)
                event_time = self.parse_time(full_text)
                price = self.extract_price(full_text)
                age_min, age_max = self.extract_age_range(full_text)

                # Summary: first paragraph or description
                summary_el = item.find(["p", "div"], class_=lambda c: c and (
                    "desc" in str(c).lower() or "summary" in str(c).lower() or "body" in str(c).lower()
                ))
                summary = summary_el.get_text(strip=True) if summary_el else None
                if not summary:
                    # Take first <p> if available
                    p = item.find("p")
                    summary = p.get_text(strip=True) if p else None

                activities.append(self.make_activity(
                    title=title,
                    city=city,
                    source_url=url,
                    summary=summary,
                    link=link,
                    event_date=event_date,
                    event_time=event_time,
                    price=price,
                    age_min=age_min,
                    age_max=age_max,
                ))

        except Exception as e:
            logger.error(f"Library scraper failed for {city}: {e}")

        return activities
