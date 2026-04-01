"""Tests for scraper parsing utilities."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper.base import BaseScraper


class DummyScraper(BaseScraper):
    category = "test"

    async def scrape(self, city):
        return []


scraper = DummyScraper()


def test_parse_french_date_full():
    assert scraper.parse_french_date("15 mars 2026") == "2026-03-15"
    assert scraper.parse_french_date("1 janvier 2026") == "2026-01-01"
    assert scraper.parse_french_date("samedi 20 avril 2026") == "2026-04-20"


def test_parse_french_date_slashes():
    assert scraper.parse_french_date("15/03/2026") == "2026-03-15"
    assert scraper.parse_french_date("01/12/2026") == "2026-12-01"


def test_parse_french_date_iso():
    assert scraper.parse_french_date("2026-04-15") == "2026-04-15"


def test_parse_french_date_empty():
    assert scraper.parse_french_date("") is None
    assert scraper.parse_french_date("no date here") is None


def test_parse_time():
    assert scraper.parse_time("14h30") == "14:30"
    assert scraper.parse_time("9h00") == "09:00"
    assert scraper.parse_time("à 15h") == "15:00"
    assert scraper.parse_time("14:30") == "14:30"
    assert scraper.parse_time("") is None


def test_extract_price():
    assert scraper.extract_price("Gratuit") == "Gratuit"
    assert scraper.extract_price("entrée libre") == "Gratuit"
    assert scraper.extract_price("5€") == "5€"
    assert scraper.extract_price("tarif: 12,50 €") == "12,50€"
    assert scraper.extract_price("") is None


def test_extract_age_range():
    assert scraper.extract_age_range("6-10 ans") == (6, 10)
    assert scraper.extract_age_range("de 5 à 8 ans") == (5, 8)
    assert scraper.extract_age_range("dès 6 ans") == (6, 12)
    assert scraper.extract_age_range("") == (5, 10)


def test_make_activity():
    act = scraper.make_activity(
        title="Test Activity",
        city="Lyon",
        source_url="https://example.com",
        summary="A test",
        event_date="2026-04-15",
    )
    assert act["title"] == "Test Activity"
    assert act["category"] == "test"
    assert act["city"] == "Lyon"
    assert act["event_date"] == "2026-04-15"
    assert act["age_min"] == 5
    assert act["age_max"] == 10
