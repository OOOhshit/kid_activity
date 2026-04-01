"""API routes for activity queries."""

from fastapi import APIRouter, Query

from db import query_activities, get_distinct_cities, get_distinct_categories
from models import ActivityListResponse

router = APIRouter(prefix="/api")


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
    return get_distinct_cities()


@router.get("/categories")
async def list_categories():
    return get_distinct_categories()
