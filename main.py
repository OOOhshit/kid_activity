"""FastAPI application entrypoint."""

import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import SCRAPE_HOUR, SCRAPE_MINUTE
from db import init_db, is_db_empty
from api.routes import router as api_router
from scraper.runner import run_all_scrapers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Initialize database
    init_db()
    logger.info("Database initialized.")

    # Schedule daily scraper
    scheduler.add_job(
        run_all_scrapers,
        "cron",
        hour=SCRAPE_HOUR,
        minute=SCRAPE_MINUTE,
        id="daily_scraper",
    )
    scheduler.start()
    logger.info(f"Scraper scheduled daily at {SCRAPE_HOUR:02d}:{SCRAPE_MINUTE:02d}")

    # Run scraper on first boot if DB is empty
    if is_db_empty():
        logger.info("Database is empty, running initial scrape...")
        asyncio.create_task(run_all_scrapers())

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler stopped.")


app = FastAPI(
    title="Kid Activity Finder",
    description="Find activities for children aged 5-10 in your city",
    version="1.0.0",
    lifespan=lifespan,
)

# API routes
app.include_router(api_router)

# Static files (frontend) — must be last so it doesn't shadow API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
