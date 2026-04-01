"""Scraper for theatre / performing arts venue pages."""

import logging
from urllib.parse import urljoin

from scraper.base import BaseScraper
from config import SCRAPER_SOURCES

logger = logging.getLogger(__name__)


class TheatreScraper(BaseScraper):
    category = "theatre"

    async def scrape(self, city: str) -> list[dict]:
        url = SCRAPER_SOURCES.get("theatre", {}).get(city)
        if not url:
            return []

        activities = []
        try:
            soup = await self.fetch_page(url)

            selectors = [
                ".spectacle-item", ".show-item", "article.spectacle",
                ".agenda-item", ".event-item", ".views-row",
                ".program-item", ".saison-item",
            ]

            items = []
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    break

            if not items:
                items = soup.find_all(["article", "div"], class_=lambda c: c and (
                    "spectacle" in str(c).lower() or "show" in str(c).lower()
                    or "event" in str(c).lower() or "program" in str(c).lower()
                ))

            for item in items:
                title_el = item.find(["h2", "h3", "h4", "a"])
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title:
                    continue

                link_el = item.find("a", href=True)
                link = urljoin(url, link_el["href"]) if link_el else None

                full_text = item.get_text(" ", strip=True)

                # Filter: only keep shows mentioning children/jeune public
                text_lower = full_text.lower()
                child_keywords = [
                    "enfant", "jeune public", "famille", "jeunesse",
                    "tout petit", "dès 5", "dès 6", "dès 7",
                    "5 ans", "6 ans", "7 ans", "8 ans",
                ]
                if not any(kw in text_lower for kw in child_keywords):
                    continue

                event_date = self.parse_french_date(full_text)
                event_time = self.parse_time(full_text)
                price = self.extract_price(full_text)
                age_min, age_max = self.extract_age_range(full_text)

                summary_el = item.find("p")
                summary = summary_el.get_text(strip=True) if summary_el else None

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
            logger.error(f"Theatre scraper failed for {city}: {e}")

        return activities
