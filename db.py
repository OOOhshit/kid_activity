"""Database initialization, inserts, and queries using SQLite."""

import sqlite3
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    summary     TEXT,
    link        TEXT,
    category    TEXT NOT NULL,
    age_min     INTEGER DEFAULT 5,
    age_max     INTEGER DEFAULT 10,
    event_date  TEXT,
    event_time  TEXT,
    price       TEXT,
    city        TEXT NOT NULL,
    source_url  TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(title, event_date, city, source_url)
);

CREATE INDEX IF NOT EXISTS idx_category ON activities(category);
CREATE INDEX IF NOT EXISTS idx_city ON activities(city);
CREATE INDEX IF NOT EXISTS idx_event_date ON activities(event_date);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and indexes if they don't exist."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.close()


def insert_activities(activities: list[dict]):
    """Insert activities, ignoring duplicates."""
    if not activities:
        return
    conn = get_connection()
    conn.executemany(
        """
        INSERT OR IGNORE INTO activities
            (title, summary, link, category, age_min, age_max,
             event_date, event_time, price, city, source_url)
        VALUES
            (:title, :summary, :link, :category, :age_min, :age_max,
             :event_date, :event_time, :price, :city, :source_url)
        """,
        activities,
    )
    conn.commit()
    conn.close()


def query_activities(
    category: str | None = None,
    city: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    age: int | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    """Query activities with optional filters. Returns (results, total_count)."""
    conditions = []
    params: list = []

    if category:
        conditions.append("category = ?")
        params.append(category)
    if city:
        conditions.append("city = ?")
        params.append(city)
    if date_from:
        conditions.append("(event_date >= ? OR event_date IS NULL)")
        params.append(date_from)
    if date_to:
        conditions.append("(event_date <= ? OR event_date IS NULL)")
        params.append(date_to)
    if age is not None:
        conditions.append("age_min <= ? AND age_max >= ?")
        params.extend([age, age])

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    conn = get_connection()

    # Total count
    count_row = conn.execute(
        f"SELECT COUNT(*) as cnt FROM activities {where}", params
    ).fetchone()
    total = count_row["cnt"]

    # Paginated results
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT * FROM activities {where} ORDER BY event_date ASC, event_time ASC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    conn.close()
    return [dict(r) for r in rows], total


def get_distinct_cities() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT city FROM activities ORDER BY city"
    ).fetchall()
    conn.close()
    return [r["city"] for r in rows]


def get_distinct_categories() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT category FROM activities ORDER BY category"
    ).fetchall()
    conn.close()
    return [r["category"] for r in rows]


def is_db_empty() -> bool:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM activities").fetchone()
    conn.close()
    return row["cnt"] == 0
