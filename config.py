"""Application configuration."""

import os

# Database
DB_PATH = os.environ.get("DB_PATH", "activities.db")

# Cities to search (French cities)
CITIES = [
    "Lyon",
    "Grenoble",
    "Saint-Étienne",
    "Villeurbanne",
    "Chambéry",
]

# Age range for target audience
AGE_MIN = 5
AGE_MAX = 10

# Scheduler: hour of day to run scraper (24h format)
SCRAPE_HOUR = 6
SCRAPE_MINUTE = 0

# HTTP settings for scrapers
REQUEST_TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (compatible; KidActivityFinder/1.0; "
    "+https://github.com/kid-activity-finder)"
)

# Scraper source URLs per category and city
# These are example targets — adapt to real websites
SCRAPER_SOURCES = {
    "library": {
        "Lyon": "https://www.bm-lyon.fr/agenda",
        "Grenoble": "https://www.bm-grenoble.fr/agenda",
        "Saint-Étienne": "https://mediatheques.saint-etienne-metropole.fr/agenda",
        "Villeurbanne": "https://mediatheque.villeurbanne.fr/agenda",
        "Chambéry": "https://www.bm-chambery.fr/agenda",
    },
    "mjc": {
        "Lyon": "https://www.mjclyon.fr/activites",
        "Grenoble": "https://www.mjc-grenoble.fr/activites",
        "Saint-Étienne": "https://www.mjc-saintetienne.fr/activites",
        "Villeurbanne": "https://www.mjc-villeurbanne.fr/activites",
        "Chambéry": "https://www.mjc-chambery.fr/activites",
    },
    "theatre": {
        "Lyon": "https://www.theatresdelyon.com/agenda",
        "Grenoble": "https://www.mc2grenoble.fr/agenda",
        "Saint-Étienne": "https://www.comedie-de-saint-etienne.fr/agenda",
        "Villeurbanne": "https://www.tnp-villeurbanne.com/agenda",
        "Chambéry": "https://www.malraux-chambery.fr/agenda",
    },
    "cinema": {
        "Lyon": "https://www.allocine.fr/seance/ville-69123/",
        "Grenoble": "https://www.allocine.fr/seance/ville-38185/",
        "Saint-Étienne": "https://www.allocine.fr/seance/ville-42218/",
        "Villeurbanne": "https://www.allocine.fr/seance/ville-69266/",
        "Chambéry": "https://www.allocine.fr/seance/ville-73065/",
    },
}
