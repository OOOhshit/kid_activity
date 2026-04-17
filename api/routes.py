"""API routes for activity queries."""

import logging

from fastapi import APIRouter, Query

from config import CITIES, SCRAPER_SOURCES
from db import query_activities, get_distinct_cities, get_distinct_categories, is_db_empty
from models import ActivityListResponse
from scraper.runner import run_all_scrapers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

KNOWN_CATEGORIES = sorted(SCRAPER_SOURCES.keys())


@router.get("/activities", response_model=ActivityListResponse)
async def list_activities(
    category: str | None = Query(None, description="Filter by category"),
    city: str | None = Query(None, description="Filter by city"),
    date_from: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    age: int | None = Query(None, ge=1, le=18, description="Child age"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    activities, total = query_activities(
        category=category,
        city=city,
        date_from=date_from,
        date_to=date_to,
        age=age,
        page=page,
        per_page=per_page,
    )
    return ActivityListResponse(
        activities=activities,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/cities")
async def list_cities():
    db_cities = get_distinct_cities()
    all_cities = sorted(set(db_cities + CITIES))
    return all_cities


@router.get("/categories")
async def list_categories():
    db_cats = get_distinct_categories()
    all_cats = sorted(set(db_cats + KNOWN_CATEGORIES))
    return all_cats


@router.get("/scraper/status")
async def scraper_status():
    """Check scraper status and DB content."""
    from db import get_connection
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as cnt FROM activities").fetchone()["cnt"]
    by_category = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM activities GROUP BY category"
    ).fetchall()
    by_city = conn.execute(
        "SELECT city, COUNT(*) as cnt FROM activities GROUP BY city"
    ).fetchall()
    conn.close()
    return {
        "total_activities": total,
        "by_category": {r["category"]: r["cnt"] for r in by_category},
        "by_city": {r["city"]: r["cnt"] for r in by_city},
    }


@router.post("/scraper/run")
async def trigger_scraper():
    """Manually trigger the scraper."""
    import asyncio
    asyncio.create_task(run_all_scrapers())
    return {"status": "Scraper started in background"}
