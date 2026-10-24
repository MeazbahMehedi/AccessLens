# Architecture and current implementation

The supplied roadmap describes a modular monolith with FastAPI, SQLAlchemy, PostgreSQL, Celery/Redis, Playwright, axe-core, custom rules, Jinja2/HTMX and exports.

This starter implementation includes:
- FastAPI routes and Jinja2 templates
- SQLAlchemy persistence with SQLite by default
- Playwright Chromium scanning
- Local optional axe-core injection plus custom DOM checks
- score calculation, issue detail table, screenshot, scan history, JSON/CSV/PDF export
- CLI and tests

For ease of local use, scans currently execute in the web request and do not use the Celery queue. Docker Compose declares PostgreSQL and Redis, but the default application database remains SQLite. To reach the complete roadmap, migrate to async PostgreSQL, add Alembic migrations and Celery worker tasks, then implement authentication, multi-page crawling, schedules/alerts, scan comparisons and CI self-scan.
