"""Base scraper with shared HTTP fetching, navigation discovery, and parsing utilities."""

import logging
import re
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

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

# Keywords that indicate agenda/events/news pages in navigation or sitemap
AGENDA_KEYWORDS = [
    "agenda", "actualite", "actualité", "actualites", "actualités",
    "evenement", "événement", "evenements", "événements",
    "event", "events", "programmation", "programme",
    "saison", "spectacle", "spectacles",
    "news", "activite", "activité", "activites", "activités",
    "animation", "animations", "sortie", "sorties",
    "jeunesse", "enfant", "enfants", "famille",
    "ateliers", "atelier", "stages",
]

# Keywords that indicate a PUNCTUAL event for families or children
FAMILY_KEYWORDS = [
    "spectacle", "spectacle jeune", "jeune public",
    "conte", "contes", "heure du conte", "lecture",
    "stage vacances", "stage enfant", "stage",
    "en famille", "pour les enfants", "pour les familles",
    "familial", "sortie famille",
    "à partir de 3", "à partir de 4", "à partir de 5",
    "à partir de 6", "à partir de 7", "à partir de 8",
    "dès 3 ans", "dès 4 ans", "dès 5 ans",
    "dès 6 ans", "dès 7 ans", "dès 8 ans",
    "3-6 ans", "4-8 ans", "5-10 ans", "6-10 ans", "6-12 ans",
    "festival", "fête", "carnaval", "kermesse",
    "chasse aux oeufs", "chasse au trésor",
    "journée portes ouvertes", "portes ouvertes",
    "vacances", "halloween", "noël", "noel", "pâques",
    "cinéma plein air", "ciné-goûter",
    "balade", "randonnée", "sortie nature",
]

# Keywords that indicate institutional/admin/recurring content to EXCLUDE
EXCLUDE_KEYWORDS = [
    # --- Petite enfance / garde ---
    "petite enfance", "relais petite enfance",
    "crèche", "creche", "halte-garderie", "garderie",
    "assistante maternelle", "assistant maternel",
    "relais assistante", "ram ",
    # --- Scolaire / périscolaire ---
    "restaurant scolaire", "restauration scolaire", "cantine",
    "vie scolaire", "établissement scolaire", "etablissement scolaire",
    "inscription scolaire", "inscriptions scolaires",
    "activité périscolaire", "activités périscolaires",
    "accueil périscolaire", "temps périscolaire",
    "périscolaire", "periscolaire",
    "carte scolaire", "transport scolaire",
    "tarif périscolaire",
    # --- Cours annuels / activités régulières ---
    "cours hebdomadaire", "cours annuel", "toute l'année",
    "septembre à juin", "de septembre à",
    "trimestre", "semestre",
    "du lundi au vendredi",
    "accueil de loisirs", "accueils de loisirs",
    "quotient familial", "quotient individuel",
    # --- Navigation / interface ---
    "règlement intérieur",
    "vos démarches", "votre mairie", "la ville et vous",
    "demande de prestation", "formulaire",
    "se connecter", "je m'inscris", "mon compte",
    "mentions légales", "politique de confidentialité",
    "plan du site", "annuaire", "newsletter",
    "espace personnel", "billetterie weezevent",
    "lire la suite", "plus de détails", "en savoir plus",
    "organigramme", "à votre service",
    "education et jeunesse",
    "des espaces de jeux", "aires de jeux",
    "parcours de santé",
    "opération tranquillité vacances",
    "l'esprit tranquille",
    "les parents concernés sont",
    "le ccas", "service aide à la personne",
    "résidence renaissance",
]

# Titles that are generic category labels, not actual events
GENERIC_TITLE_BLOCKLIST = {
    "sport", "sports", "ecriture", "écriture", "multimedia", "multimédia",
    "danse", "musique", "théâtre", "theatre", "peinture", "dessin",
    "yoga", "judo", "karaté", "karate", "gym", "gymnastique",
    "natation", "tennis", "football", "basket", "rugby",
    "arts plastiques", "arts du spectacle", "bien-être", "bien être",
    "informations", "résultats", "contact", "accueil",
    "enfance jeunesse", "enfance – jeunesse", "jeunesse",
    "familles", "seniors", "les animations seniors",
    "la saison", "en famille", "sport en famille",
    "cliquez-ici", "tout voir",
    "jeune public", "spectacle", "café lecture",
    "activités artistiques", "activités culturelles",
    "mercredi et vacances :", "mercredi et vacances",
    "activ'jeunes",
}

# Minimum title length to avoid nav items / buttons
MIN_TITLE_LENGTH = 10


class BaseScraper(ABC):
    """Abstract base class for all activity scrapers."""

    category: str = ""

    async def _get_client(self) -> httpx.AsyncClient:
        """Create a configured HTTP client."""
        return httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    async def fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch a URL and return parsed HTML."""
        async with await self._get_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")

    async def fetch_sitemap(self, base_url: str) -> list[str]:
        """Try to fetch and parse sitemap.xml, returning all URLs found."""
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        urls = []
        try:
            async with await self._get_client() as client:
                resp = await client.get(sitemap_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    # Handle sitemap index (sitemapindex > sitemap > loc)
                    sitemap_locs = soup.find_all("loc")
                    for loc in sitemap_locs:
                        urls.append(loc.get_text(strip=True))
        except Exception:
            pass
        return urls

    async def discover_agenda_pages(self, base_url: str) -> list[str]:
        """Discover agenda/events/news pages by analyzing sitemap and navigation.

        Strategy:
        1. Try sitemap.xml — filter URLs matching agenda keywords
        2. Analyze the page's navigation menu (nav, header links) for agenda links
        3. Return deduplicated list of discovered agenda page URLs
        """
        discovered = set()
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        # --- Strategy 1: Sitemap ---
        sitemap_urls = await self.fetch_sitemap(base_url)
        for url in sitemap_urls:
            url_lower = url.lower()
            # If it's a sub-sitemap, try to fetch it too
            if url_lower.endswith(".xml"):
                try:
                    sub_urls = await self.fetch_sitemap(url)
                    for sub_url in sub_urls:
                        if self._url_matches_agenda(sub_url):
                            discovered.add(sub_url)
                except Exception:
                    pass
            elif self._url_matches_agenda(url):
                discovered.add(url)

        # --- Strategy 2: Navigation menu analysis ---
        try:
            soup = await self.fetch_page(base_url)
            nav_links = self._extract_nav_links(soup, base_url)
            for link_url, link_text in nav_links:
                # Check both URL path and link text for agenda keywords
                if self._url_matches_agenda(link_url) or self._text_matches_agenda(link_text):
                    # Only keep links on the same domain
                    link_parsed = urlparse(link_url)
                    if link_parsed.netloc == base_domain or not link_parsed.netloc:
                        discovered.add(link_url)
        except Exception as e:
            logger.warning(f"Failed to analyze navigation for {base_url}: {e}")

        # If nothing found, fall back to the original URL itself
        if not discovered:
            logger.info(f"No agenda pages discovered for {base_url}, using base URL")
            discovered.add(base_url)

        logger.info(f"Discovered {len(discovered)} agenda page(s) for {base_url}")
        return list(discovered)

    def _extract_nav_links(self, soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
        """Extract links from navigation areas of the page."""
        links = []

        # Look in nav elements, header, and common menu containers
        nav_containers = soup.find_all(["nav", "header"])
        nav_containers += soup.find_all(["div", "ul"], class_=lambda c: c and any(
            kw in str(c).lower() for kw in ["menu", "nav", "navigation", "header"]
        ))

        seen_urls = set()
        for container in nav_containers:
            for a_tag in container.find_all("a", href=True):
                href = a_tag["href"].strip()
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                full_url = urljoin(base_url, href)
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    text = a_tag.get_text(strip=True).lower()
                    links.append((full_url, text))

        # Also scan all links on the page (not just nav) for strong agenda signals
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            full_url = urljoin(base_url, href)
            if full_url not in seen_urls:
                text = a_tag.get_text(strip=True).lower()
                # Only include if URL path strongly matches agenda
                if self._url_matches_agenda(full_url):
                    seen_urls.add(full_url)
                    links.append((full_url, text))

        return links

    @staticmethod
    def _url_matches_agenda(url: str) -> bool:
        """Check if a URL path contains agenda-related keywords."""
        path = urlparse(url).path.lower()
        # Strong signals in the URL path
        strong_keywords = [
            "agenda", "actualite", "actualité", "actualites", "actualités",
            "evenement", "événement", "evenements", "événements",
            "event", "events", "programmation", "programme",
            "spectacle", "spectacles", "saison",
            "animation", "animations", "activite", "activité",
            "activites", "activités", "jeunesse", "enfant",
        ]
        return any(kw in path for kw in strong_keywords)

    @staticmethod
    def _text_matches_agenda(text: str) -> bool:
        """Check if link text suggests an agenda/events page."""
        text = text.lower().strip()
        agenda_texts = [
            "agenda", "actualité", "actualités", "actualite", "actualites",
            "événements", "evenements", "programmation", "programme",
            "spectacles", "saison", "animations", "activités", "activites",
            "sorties", "que faire", "à venir", "prochainement",
            "news", "événement", "evenement",
        ]
        return any(kw in text for kw in agenda_texts)

    @staticmethod
    def is_excluded_content(text: str) -> bool:
        """Check if text matches institutional/admin content that should be excluded."""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw in text_lower for kw in EXCLUDE_KEYWORDS)

    @staticmethod
    def is_family_or_kids_event(text: str) -> bool:
        """Analyze text to determine if an event targets families or children."""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw in text_lower for kw in FAMILY_KEYWORDS)

    @staticmethod
    def looks_like_event_title(title: str) -> bool:
        """Check if a title looks like an actual event (not a nav item, URL, or generic label)."""
        title_stripped = title.strip()
        if len(title_stripped) < MIN_TITLE_LENGTH:
            return False
        title_lower = title_stripped.lower()
        # Reject URLs (including without protocol)
        if title_lower.startswith("http://") or title_lower.startswith("https://"):
            return False
        if "." in title_stripped and "/" in title_stripped and " " not in title_stripped[:30]:
            return False
        # Reject emails
        if "@" in title_stripped and "." in title_stripped:
            return False
        # Reject file references (.pdf, .doc, etc.)
        if any(title_lower.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"]):
            return False
        if ".pdf" in title_lower or ".doc" in title_lower:
            return False
        # Reject if it's mostly digits (phone numbers, zip codes)
        digits = sum(c.isdigit() for c in title_stripped)
        if digits > len(title_stripped) * 0.5:
            return False
        # Reject generic category labels
        if title_lower in GENERIC_TITLE_BLOCKLIST:
            return False
        return True

    async def scrape_agenda_page(self, url: str, city: str) -> list[dict]:
        """Scrape a single agenda page for event items.

        Extracts individual events, checks if they are family/kids-oriented,
        gets a summary, and returns activity dicts.
        """
        activities = []
        try:
            soup = await self.fetch_page(url)
        except Exception as e:
            logger.error(f"Failed to fetch agenda page {url}: {e}")
            return activities

        # Find event items using broad selectors
        items = self._find_event_items(soup)

        for item in items:
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or not self.looks_like_event_title(title):
                continue

            full_text = item.get_text(" ", strip=True)

            # Exclude institutional/admin content
            if self.is_excluded_content(title) or self.is_excluded_content(full_text):
                continue

            # Filter: only keep events relevant for families/kids
            if not self.is_family_or_kids_event(full_text) and not self.is_family_or_kids_event(title):
                continue

            # Extract link
            link_el = item.find("a", href=True)
            link = urljoin(url, link_el["href"]) if link_el else None

            # Extract structured data
            event_date = self.parse_french_date(full_text)
            event_time = self.parse_time(full_text)
            price = self.extract_price(full_text)
            age_min, age_max = self.extract_age_range(full_text)

            # Build summary from description elements or first paragraph
            summary = self._extract_summary(item, title)

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

        return activities

    @staticmethod
    def _find_event_items(soup: BeautifulSoup) -> list:
        """Find individual event items on a page using multiple strategies."""
        # Try specific selectors first
        selectors = [
            "article.event", ".agenda-item", ".event-item",
            ".views-row", ".node--type-event", "li.event",
            ".activity-item", ".activite", "article.activity",
            ".spectacle-item", ".show-item", "article.spectacle",
            ".program-item", ".saison-item", ".post-item",
            ".agenda-list article", ".field-content",
            "article", ".card", ".item",
        ]

        for selector in selectors:
            items = soup.select(selector)
            if items and len(items) >= 2:
                return items

        # Fallback: look for repeating structures with event-like class names
        items = soup.find_all(["article", "div", "li", "section"], class_=lambda c: c and any(
            kw in str(c).lower() for kw in [
                "event", "agenda", "activ", "spectacle", "show",
                "program", "item", "post", "entry", "card",
            ]
        ))
        if items:
            return items

        return []

    @staticmethod
    def _extract_summary(item, title: str) -> str | None:
        """Extract a meaningful summary from an event item."""
        # Try description/summary class elements
        summary_el = item.find(["p", "div", "span"], class_=lambda c: c and any(
            kw in str(c).lower() for kw in ["desc", "summary", "body", "chapo", "intro", "excerpt", "resume", "résumé"]
        ))
        if summary_el:
            text = summary_el.get_text(strip=True)
            if text and text != title:
                return text[:300]

        # Take first <p> that's not the title
        for p in item.find_all("p"):
            text = p.get_text(strip=True)
            if text and text != title and len(text) > 10:
                return text[:300]

        return None

    @abstractmethod
    async def scrape(self, city: str) -> list[dict]:
        """Scrape activities for a given city. Returns list of activity dicts."""
        ...

    @staticmethod
    def parse_french_date(text: str) -> str | None:
        """Parse French date text into ISO format YYYY-MM-DD."""
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
