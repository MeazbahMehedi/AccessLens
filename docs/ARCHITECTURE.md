# Architecture

AccessCheck is a local FastAPI application with server-rendered Jinja2 pages and small local JavaScript modules. It scans one public page at a time with Playwright Chromium and a bundled axe-core script.

## Request and job flow

1. `POST /scan` validates the WCAG target and public URL, creates a queued database record, then redirects to the report page.
2. An in-process asyncio task waits for one of two scan slots. Playwright runs in a dedicated thread/event loop, retaining Windows subprocess compatibility.
3. Public-target validation uses system DNS for normal public answers. A synthetic IPv4 answer in 198.18/15, synthetic IPv6 answer in 2001:2::/48, or unavailable system DNS, triggers independent A/AAAA verification over HTTPS. Real private answers and literal reserved IPs remain blocked. DNS outages are reported as connectivity failures. Concurrent resource requests share a pending destination check. Browser routing checks request destinations, including redirects and subresources. Service workers are disabled. Public-address validation is defense in depth; deployment still requires network isolation.
4. The scanner rejects HTTP errors and recognizable challenges, then executes axe-core. Failed WCAG rules become scored findings; incomplete checks and best practices become unscored review items.
5. If axe-core is unavailable, conservative basic checks run with explicit limited-coverage notes.
6. The application saves findings, review items, metadata, weighted rule scores, timestamps and optional screenshot evidence.
7. Report-page polling detects completion. The Overview polls aggregate data every ten seconds and refreshes when scan totals/statuses change.
8. Export routes offload PDF/DOCX/DOC/CSV/JSON generation from the request event loop.

## Persistence

SQLAlchemy uses asynchronous SQLite sessions. Existing SQLite databases receive additive `review_items` and `scan_metadata` columns on startup. Original records remain legacy reports and are excluded from current overview scores. This additive migration is SQLite-specific. No PostgreSQL migration workflow is supplied.

Database URLs and screenshot paths are configurable. Docker mounts `/data` only, preserving application source from being shadowed by a data volume. Scans interrupted by a restart are marked failed at the next startup.

## Interface

- `/` and `/dashboard`: overview metrics and charts.
- `/new-scan`: scan form.
- `/history`: searchable, paginated scan list.
- `/scan/{id}`: detailed evidence and status.
- `/reports`: completed downloads.
- `/developer`: fixed GitHub profile and public repositories.
- `/about`: purpose, scoring and limitations.

`/docs`, `/redoc` and OpenAPI exposure are disabled. Internal endpoints serve status, dashboard aggregates and read-only developer data. There is no public API documentation page.

## External data

Audits access the chosen public page and its resources. The developer service accesses a fixed GitHub account, caches responses for ten minutes and keeps an in-memory stale fallback. HTTPS DNS fallback sends only hostnames and record types to Google Public DNS or Cloudflare when system DNS fails or returns recognized synthetic IPv4/IPv6 addresses; successful public answers are cached for at most their address-record TTL or 60 seconds. This validation does not pin the browser connection, and the local VPN/proxy remains responsible for its network routing. Browser-side profile rendering uses text nodes for external descriptions and validates outbound link protocols.

## Browser connectivity

Chromium inherits proxy environment settings in auto mode, can use an explicit server-side proxy, or can use system networking. An explicit proxy is shared with HTTPS DNS and GitHub clients. Route metadata stores only the source of configuration. Known network failures have actionable messages and structured failure codes; selected transient connection errors receive one retry. TLS verification, private-target rejection and challenge handling remain active.

## Operational limits

Use one web worker. Queue state, concurrency control and GitHub cache are process-local. There is no distributed queue, scheduler, login system, crawler or remote deployment included. The Docker configuration provides one application service and a data volume.
