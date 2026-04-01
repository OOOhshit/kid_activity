"""Pydantic models for API request/response."""

from pydantic import BaseModel


class Activity(BaseModel):
    id: int
    title: str
    summary: str | None = None
    link: str | None = None
    category: str
    age_min: int = 5
    age_max: int = 10
    event_date: str | None = None
    event_time: str | None = None
    price: str | None = None
    city: str
    source_url: str


class ActivityListResponse(BaseModel):
    activities: list[Activity]
    total: int
    page: int
    per_page: int
