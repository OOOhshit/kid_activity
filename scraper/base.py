"""Base scraper with shared HTTP fetching, navigation discovery, and parsing utilities."""

import asyncio
import logging
import random
import re
import unicodedata
from datetime import date, timedelta
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT


def _normalize(text: str) -> str:
    """Lowercase, NFC-normalize, and unify typographic punctuation for matching."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text).lower()
    # Unify curly quotes and dashes to their ASCII equivalents
    return (
        t.replace("\u2019", "'")   # right single quote → '
         .replace("\u2018", "'")   # left single quote  → '
         .replace("\u201c", '"')
         .replace("\u201d", '"')
         .replace("\u2013", "-")   # en dash
         .replace("\u2014", "-")   # em dash
    )

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
    "gala de danse", "gala annuel", "spectacles de danses de fin d'année",
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
    # --- Admin / institutionnel supplémentaires ---
    "horaires d'ouverture", "horaires de",
    "conseil municipal", "conseil des jeunes",
    "pôle jeunesse", "pole jeunesse",
    "s.i.j", "sij du",
    "retour en photos", "retour en images",
    "collecte de sang", "don du sang",
    "sondage", "enquête publique", "enquete publique",
    "recensement", "élections", "elections",
    "travaux ", "chantier ", "déviation",
    "permanence ", "réunion publique", "reunion publique",
    "commémoration", "commemoration", "cérémonie", "ceremonie",
    "lettre du maire", "mot du maire",
    "rétrospective", "retrospective",
    "covid", "pandémie",
    "sécheresse", "canicule", "influenza",
    "au sein de", "vous souhaitez participer",
    "tier devient", "devient dott",
    "carré des arts",
    "ateliers parents-enfants", "ateliers parent-enfant",
]

# Titles that are generic category labels, not actual events
GENERIC_TITLE_BLOCKLIST = {
    "sport", "sports", "ecriture", "écriture", "multimedia", "multimédia",
    "danse", "musique", "théâtre", "theatre", "peinture", "dessin",
    "yoga", "judo", "karaté", "karate", "gym", "gymnastique",
    "natation", "tennis", "football", "basket", "rugby",
    "arts plastiques", "arts du spectacle", "bien-être", "bien être",
    "arts vivants", "arts martiaux",
    "danse contemp'jazz", "danse contemporaine", "danse classique",
    "danse jazz", "danse moderne", "danse hip-hop",
    "informations", "résultats", "contact", "accueil",
    "enfance jeunesse", "enfance – jeunesse", "jeunesse",
    "familles", "seniors", "les animations seniors",
    "la saison", "en famille", "sport en famille",
    "cliquez-ici", "tout voir",
    "jeune public", "spectacle", "café lecture",
    "activités artistiques", "activités culturelles",
    "mercredi et vacances :", "mercredi et vacances",
    "activ'jeunes", "stages vacances", "stages",
    "au sein de chanorier", "vous souhaitez participer",
    "vous souhaitez participer ?",
    "saison culturelle", "programmation scolaire",
    "spectacles amateurs",
    "avec nos partenaires", "toute la saison",
    "je réserve", "je reserve",
    "comédie musicale", "comedie musicale",
    "programme des animations",
    "activités de la bibliothèque", "activites de la bibliotheque",
    "carte des jpo des artistes 2021",
    "foot avec l'us croissy",
    "manifestations", "concours logo",
    "les nouvelles couleurs de la mpt",
    "les temps forts de notre fin de saison",
    "la 1000ième !", "la 1000ieme !",
    "ca y est la nouvelle saison a commencé !",
    "inscription : vacances scolaires",
    "accueil des mercredis et pendant les vacances scolaires",
}

# Minimum title length to avoid nav items / buttons
MIN_TITLE_LENGTH = 10

# Maximum number of agenda pages to scrape per source site
MAX_AGENDA_PAGES = 50


class BaseScraper(ABC):
    """Abstract base class for all activity scrapers."""

    category: str = ""

    _BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    async def _get_client(self) -> httpx.AsyncClient:
        """Create an HTTP client that mimics a real browser."""
        return httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers=self._BROWSER_HEADERS,
            follow_redirects=True,
        )

    async def fetch_page(self, url: str, polite_delay: bool = True) -> BeautifulSoup:
        """Fetch a URL and return parsed HTML."""
        if polite_delay:
            await asyncio.sleep(random.uniform(0.3, 1.0))
        async with await self._get_client() as client:
            parsed = urlparse(url)
            client.headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
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

        result = list(discovered)
        if len(result) > MAX_AGENDA_PAGES:
            logger.info(
                f"Limiting {len(result)} agenda pages to {MAX_AGENDA_PAGES} for {base_url}"
            )
            result = result[:MAX_AGENDA_PAGES]
        logger.info(f"Discovered {len(result)} agenda page(s) for {base_url}")
        return result

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
        text_norm = _normalize(text)
        return any(_normalize(kw) in text_norm for kw in EXCLUDE_KEYWORDS)

    @staticmethod
    def is_family_or_kids_event(text: str) -> bool:
        """Analyze text to determine if an event targets families or children."""
        if not text:
            return False
        text_norm = _normalize(text)
        return any(_normalize(kw) in text_norm for kw in FAMILY_KEYWORDS)

    @staticmethod
    def looks_like_event_title(title: str) -> bool:
        """Check if a title looks like an actual event (not a nav item, URL, or generic label)."""
        title_stripped = unicodedata.normalize("NFC", title).strip()
        if len(title_stripped) < MIN_TITLE_LENGTH:
            return False
        title_lower = _normalize(title_stripped)
        # Reject URLs (with or without protocol)
        if title_lower.startswith(("http://", "https://", "www.")):
            return False
        if "www." in title_lower or "http://" in title_lower or "https://" in title_lower:
            return False
        # Reject domain-like strings (x.fr, x.com, x.org at end of title without spaces around)
        if re.search(r"\b\w+\.(fr|com|org|net|eu)\b", title_lower):
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
        # Reject short all-caps category labels (e.g. "ARTS VIVANTS", "DANSE CONTEMP'JAZZ")
        letters = [c for c in title_stripped if c.isalpha()]
        if letters and len(title_stripped) < 40:
            uppercase_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if uppercase_ratio > 0.85:
                return False
        # Reject titles ending with ":" — they're typically labels/headers, not event names
        if title_stripped.endswith((":", "：")):
            return False
        # Reject titles that are obvious fragments/pieces
        fragment_starts = (
            "«", "»", "–", "—", "...", "…",
            "voici ", "certains de ", "liste des ",
            "galerie ", "dépliant ", "depliant ",
            "programme :", "programme:",
            "rendez-vous de ", "retrouvez ",
            "catalogue ", "administrateur", "administrator",
            "une initiative", "l'arrêté", "l'arrete", "'arrêté",
            "du côté des", "du cote des",
            "mercredi ", "jeudi ", "vendredi ", "samedi ", "dimanche ",
            "lundi ", "mardi ",
            "à voir en", "a voir en",
            "tous les évènements", "tous les evenements",
            "salle ", "spectacles passés", "spectacles passes",
            "spectacles sésame",
            "fin du ", "1. fin ", "1.fin ",
        )
        if any(title_lower.startswith(p) for p in fragment_starts):
            return False
        # Reject navigation/label-style single words or "Spectacles" etc.
        nav_labels = {
            "spectacles", "événements", "evenements", "saison",
            "programmation", "agenda", "activités", "activites",
        }
        if title_lower in nav_labels:
            return False
        return True

    @staticmethod
    def is_punctual_event(text: str) -> bool:
        """Check whether the text describes a PUNCTUAL (one-off/limited-date) event."""
        if not text:
            return False
        text_lower = _normalize(text)
        punctual_markers = [
            "spectacle", "concert", "festival", "fête", "fete",
            "conte", "contes", "lecture",
            "stage", "stages", "vacances",
            "portes ouvertes", "kermesse", "carnaval",
            "chasse aux oeufs", "chasse au trésor",
            "atelier vacances", "stage vacances",
            "ciné-goûter", "cine-gouter", "cinéma plein air",
            "halloween", "noël", "noel", "pâques", "paques",
            "exposition",
            "représentation", "representation",
        ]
        return any(m in text_lower for m in punctual_markers)

    @staticmethod
    def is_past_event(title: str, full_text: str, event_date: str | None) -> bool:
        """Detect if an event is clearly in the past and should be skipped."""
        today = date.today()
        current_year = today.year

        # If we extracted a specific date, check it directly
        if event_date:
            try:
                ed = date.fromisoformat(event_date)
                if ed < today - timedelta(days=30):
                    return True
            except ValueError:
                pass

        # Check for past years in the TITLE only (not full text to avoid
        # false positives from copyright notices, footers, etc.)
        title_norm = _normalize(title)
        for year in range(2000, current_year):
            if str(year) in title_norm:
                return True

        return False

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

            # Require PUNCTUAL event signals (not annual classes)
            if not (self.is_punctual_event(title) or self.is_punctual_event(full_text)):
                continue

            # Filter: only keep events relevant for families/kids
            if not self.is_family_or_kids_event(full_text) and not self.is_family_or_kids_event(title):
                continue

            # Extract link
            link_el = item.find("a", href=True)
            link = urljoin(url, link_el["href"]) if link_el else None

            # Extract structured data
            event_date = self.parse_french_date(full_text)

            # Skip events clearly in the past
            if self.is_past_event(title, full_text, event_date):
                continue

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
    def _is_in_nav(el) -> bool:
        """Check if an element sits inside a nav/footer/sidebar (3 levels max)."""
        nav_tags = {"nav", "footer", "aside"}
        nav_classes = {"menu", "nav", "sidebar", "breadcrumb", "footer-widget", "footer-area"}
        for i, parent in enumerate(el.parents):
            if i > 4:
                break
            if parent.name in nav_tags:
                return True
            parent_classes = set(parent.get("class", [])) if hasattr(parent, "get") else set()
            if parent_classes & nav_classes:
                return True
        return False

    @staticmethod
    def _find_event_items(soup: BeautifulSoup) -> list:
        """Find individual event items on a page using multiple strategies."""

        def _keep(el):
            return len(el.get_text(strip=True)) > 30 and not BaseScraper._is_in_nav(el)

        # Strategy 1: CMS-specific selectors (most precise)
        specific_selectors = [
            "article.event", ".agenda-item", ".event-item",
            ".views-row", ".node--type-event", "li.event",
            ".activity-item", ".activite", "article.activity",
            ".spectacle-item", ".show-item", "article.spectacle",
            ".program-item", ".saison-item",
            ".tribe-events-calendar-list__event",
            ".bandeau_item", ".film",
            ".list_item", ".post-item",
        ]
        for selector in specific_selectors:
            items = [el for el in soup.select(selector) if _keep(el)]
            if len(items) >= 2:
                return items

        # Strategy 2: Auto-detect repeating structures with content
        class_groups: dict[str, list] = {}
        for el in soup.find_all(["article", "div", "li", "section"], class_=True):
            if not _keep(el):
                continue
            key = " ".join(sorted(el.get("class", [])))
            class_groups.setdefault(key, []).append(el)

        best_group = None
        best_score = 0
        for key, elements in class_groups.items():
            if len(elements) < 2:
                continue
            avg_len = sum(len(el.get_text(strip=True)) for el in elements) / len(elements)
            has_headings = any(el.find(["h2", "h3", "h4"]) for el in elements)
            has_links = any(el.find("a", href=True) for el in elements)
            score = len(elements) * (avg_len ** 0.5) * (2 if has_headings else 1) * (1.5 if has_links else 1)
            if score > best_score:
                best_score = score
                best_group = elements

        if best_group and len(best_group) >= 2:
            return best_group

        # Strategy 3: fall back to generic article tags with meaningful content
        for selector in ["article", ".card"]:
            items = [el for el in soup.select(selector) if _keep(el)]
            if len(items) >= 2:
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
        """Extract price information from text. Optional — returns None if no price found."""
        if not text:
            return None
        text_lower = _normalize(text)

        # --- Free / gratuit ---
        free_markers = [
            "gratuit", "gratuite", "gratuits", "gratuites",
            "entrée libre", "entree libre",
            "accès libre", "acces libre",
            "participation libre", "sans frais",
        ]
        if any(m in text_lower for m in free_markers):
            return "Gratuit"

        # --- Price range: "5 à 15€", "de 5 à 15 euros", "entre 5 et 15€" ---
        range_match = re.search(
            r"(?:de\s+|entre\s+)?(\d+(?:[.,]\d{1,2})?)\s*(?:à|a|et|-)\s*"
            r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur\b|euros?\b)",
            text_lower,
        )
        if range_match:
            low = range_match.group(1).replace(",", ".")
            high = range_match.group(2).replace(",", ".")
            return f"{low}€ - {high}€"

        # --- "À partir de X€" / "Dès X€" ---
        from_match = re.search(
            r"(?:à\s+partir\s+de|a\s+partir\s+de|dès|des)\s+"
            r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur\b|euros?\b)",
            text_lower,
        )
        if from_match:
            amount = from_match.group(1).replace(",", ".")
            return f"À partir de {amount}€"

        # --- Simple: "5€", "5 €", "5,50€", "5 euros" ---
        simple_match = re.search(
            r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur\b|euros?\b)",
            text_lower,
        )
        if simple_match:
            amount = simple_match.group(1).replace(",", ".")
            return f"{amount}€"

        # --- € before number: "€ 5" ---
        euro_first = re.search(r"€\s*(\d+(?:[.,]\d{1,2})?)", text_lower)
        if euro_first:
            amount = euro_first.group(1).replace(",", ".")
            return f"{amount}€"

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
