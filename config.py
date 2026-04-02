"""Application configuration."""

import os

# Database
DB_PATH = os.environ.get("DB_PATH", "activities.db")

# Cities to search (French cities)
CITIES = [
    "Le Pecq",
    "Chatou",
    "Croissy-sur-Seine",
    "Montesson",
    "Saint-Germain-en-Laye",
    "Rueil-Malmaison",
    "Nanterre",
    "Bougival",
    "Marly-le-Roi",
    "La Celle-Saint-Cloud",
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
        "Le Vésinet": "https://www.boucledesmediatheques.fr/opac/cms/articleviewrecent/nb/50",
        "Le Pecq": "https://lepecq-pom.c3rb.org/index.php/agenda/bibliotheques-municipales",
        "Chatou": "https://mediatheque.chatou.fr/",
        "Croissy-sur-Seine": "https://bibliotheque.croissy.com/",
        "Montesson": "https://montesson.fr/mediatheque-louis-aragon/",
        "Saint-Germain-en-Laye": "https://mediatheques.saintgermainenlaye.fr/",
        "Rueil-Malmaison": "https://mediatheques.mairie-rueilmalmaison.fr/",
        "Nanterre": "https://mediatheques.nanterre.fr/",
        "Bougival": "https://www.bougival.fr/bibliotheque/",
        "Marly-le-Roi": "https://marlyleroi.fr/mediatheque-pierre-bourdan/",
        "La Celle-Saint-Cloud": "https://lacellesaintcloud.fr/culture/bibliotheque/",
    },
    "mjc": {
        "Le Vésinet": "https://www.mjclevesinet.fr/activites",
        "Le Pecq": "https://mptccam.goasso.org/activites",
        "Chatou": "https://mjcchatou.org/",
        "Croissy-sur-Seine": "https://jeunessecroissy.fr/",
        "Montesson": "https://www.mjcmontesson.com/",
        "Saint-Germain-en-Laye": "https://laclef.aniapp.fr/activites",
        "Rueil-Malmaison": "https://www.mjc-rueil.asso.fr/",
        "Nanterre": "https://www.maisons-pour-tous-nanterre.fr/",
        "Bougival": "https://www.ville-bougival.fr/vie-associative/associations-culturelles/",
        "Marly-le-Roi": "https://mjcmarly.asso.fr/",
        "La Celle-Saint-Cloud": "https://lacellesaintcloud.fr/jeunesse/la-kab-mjc/",
    },
    "theatre": {
        "Le Vésinet": "https://www.vesinet.org/programmation/",
      "Le Pecq": "https://www.ville-lepecq.fr/lequai3",
      "Chatou": "https://www.chatou.fr/mon-quotidien/culture/centre-culturel-et-de-loisirs",
      "Croissy-sur-Seine": "https://www.croissy.com/agenda",
      "Montesson": "https://www.montesson.fr/agenda/",
      "Saint-Germain-en-Laye": "https://tad.saintgermainenlaye.fr/1845/saison", 
      "Rueil-Malmaison": "https://www.tam.fr",
      "Nanterre": "https://www.nanterre-amandiers.com/",
      "Bougival": "https://www.ville-bougival.fr/bouger-sortir/culture/theatre-du-grenier/",
      "Marly-le-Roi": "https://www.ccjeanvilar.fr/",
      "La Celle-Saint-Cloud": "https://www.culture-lacellesaintcloud.fr/"
    },
}
