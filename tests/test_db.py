"""Tests for database operations."""

import os
import sys
import tempfile

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config

from db import init_db, insert_activities, query_activities, get_connection


def setup_function():
    """Use a fresh temp DB for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    config.DB_PATH = path


def teardown_function():
    """Clean up temp DB."""
    try:
        os.unlink(config.DB_PATH)
    except OSError:
        pass


def test_init_db():
    init_db()
    conn = get_connection()
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='activities'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_insert_and_query():
    init_db()
    activities = [
        {
            "title": "Atelier Lecture",
            "summary": "Lecture pour enfants",
            "link": "https://example.com/lecture",
            "category": "library",
            "age_min": 5,
            "age_max": 10,
            "event_date": "2026-04-15",
            "event_time": "14:00",
            "price": "Gratuit",
            "city": "Lyon",
            "source_url": "https://bm-lyon.fr/agenda",
        },
        {
            "title": "Spectacle Marionnettes",
            "summary": "Spectacle jeune public",
            "link": "https://example.com/marionnettes",
            "category": "theatre",
            "age_min": 4,
            "age_max": 8,
            "event_date": "2026-04-20",
            "event_time": "10:30",
            "price": "5€",
            "city": "Grenoble",
            "source_url": "https://mc2grenoble.fr/agenda",
        },
    ]
    insert_activities(activities)

    results, total = query_activities()
    assert total == 2
    assert len(results) == 2


def test_dedup():
    init_db()
    activity = {
        "title": "Atelier Peinture",
        "summary": "Peinture pour enfants",
        "link": None,
        "category": "mjc",
        "age_min": 6,
        "age_max": 10,
        "event_date": "2026-05-01",
        "event_time": "15:00",
        "price": "3€",
        "city": "Lyon",
        "source_url": "https://mjc-lyon.fr/activites",
    }
    insert_activities([activity])
    insert_activities([activity])  # Duplicate

    results, total = query_activities()
    assert total == 1


def test_filter_by_city():
    init_db()
    insert_activities([
        {
            "title": "A1", "summary": None, "link": None, "category": "library",
            "age_min": 5, "age_max": 10, "event_date": "2026-04-15",
            "event_time": None, "price": None, "city": "Lyon",
            "source_url": "https://example.com/1",
        },
        {
            "title": "A2", "summary": None, "link": None, "category": "library",
            "age_min": 5, "age_max": 10, "event_date": "2026-04-15",
            "event_time": None, "price": None, "city": "Grenoble",
            "source_url": "https://example.com/2",
        },
    ])

    results, total = query_activities(city="Lyon")
    assert total == 1
    assert results[0]["city"] == "Lyon"


def test_filter_by_age():
    init_db()
    insert_activities([
        {
            "title": "For 5-8", "summary": None, "link": None, "category": "mjc",
            "age_min": 5, "age_max": 8, "event_date": "2026-04-15",
            "event_time": None, "price": None, "city": "Lyon",
            "source_url": "https://example.com/1",
        },
        {
            "title": "For 9-12", "summary": None, "link": None, "category": "mjc",
            "age_min": 9, "age_max": 12, "event_date": "2026-04-15",
            "event_time": None, "price": None, "city": "Lyon",
            "source_url": "https://example.com/2",
        },
    ])

    results, total = query_activities(age=7)
    assert total == 1
    assert results[0]["title"] == "For 5-8"
