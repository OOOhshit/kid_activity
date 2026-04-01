"""Scraper for cinema pages (family/children screenings)."""

import logging
from urllib.parse import urljoin

from scraper.base import BaseScraper
from config import SCRAPER_SOURCES

logger = logging.getLogger(__name__)


class CinemaScraper(BaseScraper):
    category = "cinema"

    async def scrape(self, city: str) -> list[dict]:
        url = SCRAPER_SOURCES.get("cinema", {}).get(city)
        if not url:
            return []

        activities = []
        try:
            soup = await self.fetch_page(url)

            selectors = [
                ".card-movie", ".movie-card", ".film-item",
                ".entity-card", ".mdl-card", ".gd-col",
                "article.movie", ".movie-item",
            ]

            items = []
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    break

            if not items:
                items = soup.find_all(["article", "div", "li"], class_=lambda c: c and (
                    "movie" in str(c).lower() or "film" in str(c).lower()
                    or "card" in str(c).lower()
                ))

            for item in items:
                title_el = item.find(["h2", "h3", "h4", "a"])
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title:
                    continue

                full_text = item.get_text(" ", strip=True)

                # Filter: only keep family/children films
                text_lower = full_text.lower()
                child_keywords = [
                    "enfant", "famille", "animation", "jeune public",
                    "tout public", "à partir de 5", "à partir de 6",
                    "dès 5 ans", "dès 6 ans",
                ]
                if not any(kw in text_lower for kw in child_keywords):
                    continue

                link_el = item.find("a", href=True)
                link = urljoin(url, link_el["href"]) if link_el else None

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
            logger.error(f"Cinema scraper failed for {city}: {e}")

        return activities
