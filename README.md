# AccessCheck

AccessCheck is a local-first website accessibility analysis app. It accepts a public website URL, checks common WCAG accessibility issues, calculates an indicative score, saves scan history, highlights findings in a screenshot, and exports JSON/CSV/PDF reports.

> **Implementation note:** this ZIP is a runnable MVP built from the supplied roadmap. It includes a working FastAPI web UI, Playwright scanner, custom checks, SQLite local storage, report exports, and tests. Docker Compose also provides PostgreSQL/Redis/Celery services for the roadmap architecture, but this MVP's web flow runs scans synchronously and uses SQLite by default so it is straightforward to run locally. The advanced roadmap features (multi-user auth, scheduled scans, production deployment, full HTMX workflow and exhaustive axe rule coverage) are not yet implemented. Accessibility scores are indicative and are not a legal compliance certification.

## Features
- Public HTTP/HTTPS URL validation with private/local address rejection
- Playwright Chromium browser rendering and screenshot capture
- Optional local axe-core integration when `app/engine/vendor/axe.min.js` exists
- Custom checks for page title/lang, headings, image alt, form labels, vague/empty links, landmarks and small targets
- Issue severity, WCAG mapping, score and principle scores
- Scan history page and results dashboard
- JSON, CSV and PDF exports (PDF requires WeasyPrint system libraries)
- CLI scanner
- pytest tests

## Quick start (Python 3.11+)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

### Add axe-core (recommended)
The scanner uses axe-core from a local JavaScript file when present. To fetch the upstream open-source file once:
```bash
python scripts/fetch_axe.py
```
This is an optional setup-time download; scans do not call a third-party API. If the file is absent, custom checks still run.

## Docker
```bash
docker compose up --build
```
The Compose web container uses PostgreSQL and Redis configuration but the current MVP database layer is SQLite-first. For easiest reproducible use, run the Python quick start above. See `docs/ARCHITECTURE.md` for scope and next steps.

## Usage
- Web: submit a public website URL at `/`
- API docs: `/docs`
- JSON API: `POST /api/scans` with `{"url":"https://example.com","wcag_level":"AA"}`; returns a scan ID and result URL
- Get a scan: `GET /api/scans/{scan_id}`
- Export: `/scan/{scan_id}/export?format=json|csv|pdf`
- CLI: `accesscheck scan https://example.com --fail-under 80`

## Security
Only scan websites you are authorized to test. URL checks reject local/private IP addresses and re-check redirects. This is defense in depth, not a guarantee against every network edge case; use an outbound network policy in deployment. Do not expose the development server to the public internet without authentication, rate limiting, isolation, and a production configuration.

## Tests
```bash
pytest
```
