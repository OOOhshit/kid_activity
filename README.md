/home/user/kid_activity/
├── .gitignore
├── requirements.txt        # Python dependencies
├── config.py               # Cities, scraper URLs, settings
├── db.py                   # SQLite database layer
├── models.py               # Pydantic models
├── main.py                 # FastAPI app entrypoint (run this)
├── api/
│   ├── __init__.py
│   └── routes.py           # REST API endpoints
├── scraper/
│   ├── __init__.py
│   ├── base.py             # Base scraper + French date/time parsers
│   ├── library.py          # Library scraper
│   ├── mjc.py              # MJC scraper
│   ├── theatre.py          # Theatre scraper
│   ├── cinema.py           # Cinema scraper
│   └── runner.py           # Orchestrator
├── static/
│   ├── index.html          # Frontend page
│   ├── style.css           # Styles
│   └── app.js              # Frontend logic
└── tests/
    ├── __init__.py
    ├── test_db.py           # DB tests
    └── test_scraper.py      # Parser tests
