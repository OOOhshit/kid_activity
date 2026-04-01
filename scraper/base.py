"""Base scraper with shared HTTP fetching and parsing utilities."""

import logging
import re
from abc import ABC, abstractmethod

import httpx
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

# French month names to month numbers
FRENCH_MONTHS = {
    "janvier": "01", "février": "02", "mars": "03", "avril": "04",
    "mai": "05", "juin": "06", "juillet": "07", "août": "08",
    "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
    # Abbreviated
    "janv": "01", "févr": "02", "avr": "04",
    "juil": "07", "sept": "09", "oct": "10", "nov": "11", "déc": "12",
}


class BaseScraper(ABC):
    """Abstract base class for all activity scrapers."""

    category: str = ""

    async def fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch a URL and return parsed HTML."""
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")

    @abstractmethod
    async def scrape(self, city: str) -> list[dict]:
        """Scrape activities for a given city. Returns list of activity dicts."""
        ...

    @staticmethod
    def parse_french_date(text: str) -> str | None:
        """Parse French date text into ISO format YYYY-MM-DD.

        Handles formats like:
        - "15 mars 2026"
        - "15/03/2026"
        - "samedi 15 mars 2026"
        """
        if not text:
            return None

        text = text.strip().lower()

        # Try DD/MM/YYYY
        match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # Try "DD month YYYY" (with optional day name prefix)
        for month_name, month_num in FRENCH_MONTHS.items():
            pattern = rf"(\d{{1,2}})\s+{re.escape(month_name)}\.?\s+(\d{{4}})"
            match = re.search(pattern, text)
            if match:
                day, year = match.groups()
                return f"{year}-{month_num}-{day.zfill(2)}"

        # Try YYYY-MM-DD (already ISO)
        match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def parse_time(text: str) -> str | None:
        """Extract time in HH:MM format from text."""
        if not text:
            return None
        match = re.search(r"(\d{1,2})[hH:](\d{2})", text)
        if match:
            hour, minute = match.groups()
            return f"{hour.zfill(2)}:{minute}"
        # Try just "15h"
        match = re.search(r"(\d{1,2})[hH]\b", text)
        if match:
            return f"{match.group(1).zfill(2)}:00"
        return None

    @staticmethod
    def extract_price(text: str) -> str | None:
        """Extract price information from text."""
        if not text:
            return None
        text_lower = text.lower()
        if "gratuit" in text_lower or "libre" in text_lower:
            return "Gratuit"
        match = re.search(r"(\d+(?:[.,]\d{1,2})?)\s*€", text)
        if match:
            return f"{match.group(1)}€"
        return None

    @staticmethod
    def extract_age_range(text: str) -> tuple[int, int]:
        """Extract age range from text, defaulting to 5-10."""
        if not text:
            return 5, 10
        # "6-10 ans", "de 5 à 10 ans", "dès 6 ans"
        match = re.search(r"(\d{1,2})\s*[-àa]\s*(\d{1,2})\s*ans", text.lower())
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"d[eè]s\s+(\d{1,2})\s*ans", text.lower())
        if match:
            return int(match.group(1)), 12
        return 5, 10

    def make_activity(
        self,
        title: str,
        city: str,
        source_url: str,
        summary: str | None = None,
        link: str | None = None,
        event_date: str | None = None,
        event_time: str | None = None,
        price: str | None = None,
        age_min: int = 5,
        age_max: int = 10,
    ) -> dict:
        """Create a standardized activity dict."""
        return {
            "title": title.strip(),
            "summary": summary.strip() if summary else None,
            "link": link,
            "category": self.category,
            "age_min": age_min,
            "age_max": age_max,
            "event_date": event_date,
            "event_time": event_time,
            "price": price,
            "city": city,
            "source_url": source_url,
        }
