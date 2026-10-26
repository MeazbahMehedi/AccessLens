<div align="center">

<img src="app/web/static/accesslens-logo.svg" width="80" alt="AccessLens logo">

# AccessLens

### Understand accessibility. Inspect the evidence. Share a plan.

A local-first website accessibility scanner with a multi-page dashboard, WCAG findings, screenshot evidence and downloadable reports.

**Python 3.11+ · FastAPI · Playwright · axe-core · SQLite · MIT**

[Quick start](#quick-start) · [Workspace](#workspace-pages) · [How it works](#how-it-works) · [Reports](#report-exports) · [Troubleshooting](#troubleshooting) · [Developer](https://github.com/MeazbahMehedi)

</div>

---

## What is AccessLens?

AccessLens helps developers, students and small teams identify common accessibility barriers in a web page. Enter a public URL, let a real Chromium browser render it, and explore findings with the affected HTML, WCAG criteria, severity and suggested fixes.

The application saves scan history locally, summarizes results in charts, and produces reports for development work, coursework or team review. A dedicated About page explains the method, and a Developer page displays live public GitHub information.

AccessLens evaluates **one page at one desktop viewport and one captured state**. It does not certify WCAG conformance. Automated evidence should be reviewed alongside keyboard, screen reader and task-based testing.

## Why use AccessLens?

AccessLens brings page rendering, automated findings, screenshots, saved history and report exports into one local workspace. It helps you turn an accessibility finding into a reviewable task: inspect the affected element, read the criterion and suggested fix, and share the evidence. Bundled browser checks and transparent scoring also make it suitable for repeatable coursework demonstrations.

## Core programming and technologies

**Python is the core programming language.** JavaScript runs the in-browser accessibility checks and the dashboard interactions. The project does not use an AI model or an LLM API.

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Web application | Python, FastAPI, Jinja2, Uvicorn | Routes, forms, server-rendered pages, background scan tasks and downloads |
| Browser scanning | Playwright, Chromium, JavaScript | Render one target page, evaluate its captured state and save screenshot evidence |
| Accessibility checks | Bundled axe-core and basic-check JavaScript | Supported automated WCAG rules, review items and best practices |
| Scoring | Python | Severity-weighted, rule-capped prioritization and principle scores |
| Persistence | SQLAlchemy, aiosqlite, SQLite | Scan history, findings, result metadata and status |
| Reports | ReportLab, python-docx, Python CSV/JSON | PDF, DOCX, legacy DOC/RTF, CSV and JSON exports |
| Interface | HTML, local CSS, JavaScript, SVG | Existing dashboard, charts, filtering, navigation, themes and new logo |
| Integrations | HTTPX, GitHub REST API | Read-only public developer information and repositories |
| CLI and configuration | Typer, Pydantic Settings | Command-line scanning, environment variables and `.env` configuration |
| Verification | pytest, pytest-asyncio, Playwright | URL/network checks, browser fixtures, scoring, persistence, routes and exports |

The architecture is a **modular monolith**: one Python application serves the interface and coordinates bounded browser jobs, while separate modules handle target validation, scanning, persistence, scoring and reports. The CLI reuses the same scanner.

## Main capabilities

- Render JavaScript-driven pages with Playwright Chromium.
- Evaluate supported WCAG 2.2 A, AA and AAA rules with a bundled axe-core engine.
- Separate automated WCAG failures, inconclusive checks and best-practice recommendations.
- Prioritize findings by severity, inspect element evidence and read remediation guidance.
- View a heuristic score, WCAG-principle scores, recent-score chart and severity distribution.
- Save scan history with URL/title search, status filters and pagination.
- Export PDF, editable Word, legacy Word-compatible DOC, CSV and JSON reports.
- Inspect screenshots with located failing elements outlined.
- Use separate workspace pages, responsive navigation, light/dark themes and reduced-motion support.
- Retrieve the fixed developer's public GitHub profile and searchable repository list.
- Validate public destinations, including public hostnames behind VPN/proxy synthetic DNS.
- Operate without a paid accessibility service, AI API key, Redis or an external database server.

## Workspace pages

| Page | Purpose |
| --- | --- |
| **Overview** | Saved-result metrics, recent score history, severity chart and latest scans |
| **New scan** | Public website address, WCAG target selection and scan submission |
| **Scan history** | Search, filter and reopen saved or in-progress scans |
| **Scan report** | Status, coverage notes, scores, severity counts, findings, manual-review items and screenshots |
| **Reports** | Search completed reports and download them in the required format |
| **Developer** | Live public GitHub profile and repositories for MeazbahMehedi |
| **About** | Program purpose, workflow, scoring, scope and official accessibility resources |

## Requirements

- Python **3.11 or newer**.
- An internet connection for public websites, GitHub data and initial dependency/browser installation.
- Chromium installed through Playwright.
- A writable directory for SQLite and screenshots.

PDF and Word generation use Python libraries. They do not require Microsoft Office, WeasyPrint, GTK or Cairo to be installed.

## Quick start

Extract the project and open a terminal in the directory containing `pyproject.toml`.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m playwright install chromium
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

These commands use the virtual environment directly, so PowerShell activation-policy changes are unnecessary.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
python -m uvicorn app.main:app --reload
```

For a minimal Linux installation that lacks browser system libraries:

```bash
python -m playwright install --with-deps chromium
```

Open **http://127.0.0.1:8000**. Use one server worker; the scan queue and GitHub cache live in that process.

### Project rename and existing workspaces

The project is now **AccessLens**. The ZIP and root folder are `AccessLens`, the installed project/CLI name is `accesslens`, and report downloads use the `accesslens-` prefix. The server command remains `python -m uvicorn app.main:app --reload`. Scanner behavior, WCAG rules, scoring, public-target restrictions, networking support, pages and developer identity are retained.

Stop the old server and back up its database, `.env` and screenshot directory. Copy those files into the new project root before starting, preserving any custom screenshot paths. New installations use `accesslens.db`. Without an explicit `DATABASE_URL`, an existing `accesscheck.db` is opened in place if `accesslens.db` does not exist. An existing `.env` with `DATABASE_URL` continues to select that database. Do not overwrite that `.env` with the new example when upgrading.

The CLI is now `accesslens`; reinstall the project from the new folder to register the renamed command. Existing browser theme choices are retained. Docker users must explicitly reconnect their existing volume when changing the Compose project/folder name and keep `DATABASE_URL` pointed at the database filename inside that volume; the newly named default volume starts a fresh workspace.

### Keeping an existing workspace

For this release, stop the old server with **Ctrl+C**, replace the application source, reinstall using the same virtual-environment Python, and start the server from the updated project directory. Open `http://127.0.0.1:8000/health` and confirm version **2.0.2**; a different version means an older server or project folder is still running.


Back up and retain your database (`accesslens.db`, or the existing `accesscheck.db`), `.env` and screenshot directory before replacing application files. Reinstall the project dependencies, then restart the server. Supported SQLite schema additions are applied automatically. Existing legacy scans remain available; rerun them to obtain the current engine's findings and scoring.

A distributed source ZIP does not include another installation's database, screenshots, virtual environment or private `.env`. A fresh workspace creates its database on startup.

## Using the application

1. Open **New scan** and enter a public page URL. A hostname such as `example.com` is accepted; HTTPS is added automatically.
2. Choose **A**, **AA** or **AAA**. AA is the default. Higher targets include the lower-level checks that the engine supports.
3. Start the scan. The report page shows its queued/running state and updates on completion.
4. Read the coverage notes and confirm that the captured page is the page you intended to inspect.
5. Review the score and severity counts. Open a finding to see the selector, HTML evidence, criterion and suggested fix.
6. Search findings or filter by severity. Check **Review & best practices** for items requiring human judgment.
7. Open the captured screenshot, download a report, or revisit the result later in History.

Overview metrics refresh from saved results. Failed and unfinished attempts do not contribute accessibility scores. Legacy scores are excluded from current-engine aggregates. Recent-score charts can contain different URLs or WCAG targets, so interpret comparisons in context.

## How it works

| Component | Responsibility |
| --- | --- |
| FastAPI | Web routes, scan submission, status polling and downloads |
| Jinja2 + local JavaScript/CSS | Multi-page interface, charts, filters, themes and interactions |
| Playwright Chromium | Render the requested page and capture evidence |
| axe-core | Run supported WCAG and best-practice checks in the rendered document |
| Basic checks | Limited fallback when the axe-core bundle cannot execute |
| SQLAlchemy + SQLite | Store scan records, findings, metadata and history |
| ReportLab + python-docx | Generate PDF and Word documents locally |
| GitHub REST service | Retrieve the fixed developer's public profile and repositories |

Scans run as background tasks, with up to two active browser jobs at once and a bounded admission check for queued/running work. Status polling updates the result page. On startup, scans interrupted by an earlier server shutdown are marked failed so they do not remain stuck.

The application opens the page without signing in, submitting forms, accepting consent or solving verification challenges. Its screenshot and findings reflect that visitor state.

## Understanding the findings

| Result category | Meaning | Reduces the score? |
| --- | --- | --- |
| **Confirmed findings** | A supported automated WCAG rule reported a failure on an element | Yes |
| **Manual review** | A check was incomplete or could not decide automatically | No |
| **Best practices** | A recommendation beyond the selected WCAG rules | No |

“Confirmed” identifies the automated failure category; the finding still needs contextual review. Examples include missing accessible names, missing text alternatives and other failures detected by the installed engine. A missing `<h1>` or main landmark alone is treated as a best-practice recommendation rather than automatic proof of WCAG failure.

A major website can have accessibility barriers. The exact output also depends on content, region, consent dialogs, viewport and loading state. A finding on one captured page should not be read as a verdict on an entire website.

### Scores

AccessLens uses a transparent prioritization heuristic:

```text
rule penalty = highest severity weight × (1 + 0.25 × (min(occurrences, 5) − 1))
score        = round(max(0, 100 − sum(rule penalties)))
```

| Severity | Weight |
| --- | ---: |
| Critical | 10 |
| Serious | 7 |
| Moderate | 3 |
| Minor | 1 |

Repeated instances of a rule increase its penalty up to twice the severity weight. Manual review and best practices are excluded. Perceivable, Operable, Understandable and Robust principle scores use the same formula on their assigned findings.

A score of 100 means that the checks which ran found no scored failures. The score is not a WCAG-compliance percentage or a Lighthouse score.

### Scope and coverage

- **Page scope:** one rendered URL; no site-wide crawler.
- **Viewport:** 1366 × 900 CSS pixels.
- **Timing:** initial page load followed by a short best-effort settling period.
- **Screenshot:** captured page state, capped at 16,000 pixels in height; screenshot failure does not discard saved findings.
- **Embedded content:** iframe/shadow-DOM targets can need additional review and may not be highlightable in the top document.
- **Engine fallback:** a missing/unusable axe-core bundle produces a clearly labeled Basic checks report with limited coverage.
- **Unavailable page:** HTTP error pages and recognizable anti-bot challenges fail the scan rather than receive an intended-page score.

## Report exports

Download a completed scan from its report header or the Reports page.

| Format | Suitable for | Included information |
| --- | --- | --- |
| **PDF** | Sharing and printing | Scope, notes, summary, element evidence, remediation and review items |
| **Word (.docx)** | Editing a document | Editable scan summary, findings and review guidance |
| **DOC** | Legacy Word-compatible workflows | RTF content with a `.doc` filename; use DOCX for modern Word |
| **CSV** | Excel and data analysis | Finding/review rows, source and metadata columns, coverage, notes and limitations |
| **JSON** | Structured processing | Versioned scan data, timestamps, scores, metadata, findings and review items |

CSV uses a UTF-8 BOM for spreadsheet compatibility and protects text cells against formula interpretation. Empty reports retain an identifying summary row. The interface shows download errors, and unfinished/failed scans cannot be exported. PDF/DOCX output is not an accessibility-certified document format; PDF output is not tagged.

## Network and VPN/proxy compatibility

AccessLens accepts **public websites** and rejects local, private, link-local, multicast and reserved IP destinations.

Some VPN/proxy DNS systems assign synthetic IPv4 addresses in `198.18.0.0/15` (such as `198.18.0.56`) and synthetic IPv6 addresses in `2001:2::/48` (such as `2001:2::d`) to ordinary public hostnames. AccessLens recognizes either family, including mixed A/AAAA answers. Those local DNS substitutions alone do not establish that the named website is private.

The default validation process is:

1. Validate the URL syntax, scheme, credentials and hostname.
2. Check normal system DNS answers.
3. If DNS returns a recognized synthetic IPv4 or IPv6 address, or system DNS fails, verify the hostname through HTTPS DNS using Google Public DNS, with Cloudflare as a backup for resolver/request failures.
4. Check **both A and AAAA** answers and require every returned address to be public. Genuine private answers are not replaced by an alternate resolver's public answer.
5. Continue using the original website hostname, preserving normal HTTPS/SNI and the user's existing proxy routing.

Direct URLs such as `http://198.18.0.56`, `http://[2001:2::d]`, `http://127.0.0.1` and private LAN addresses remain blocked. Mixed public/private results are rejected. If HTTPS verification cannot complete, the app reports a DNS/connectivity error; it does not silently permit the destination.

Only successful public HTTPS-DNS results are cached, for no longer than their address-record TTL or 60 seconds, whichever is shorter. HTTPS fallback sends the **hostname and DNS record type**, not the URL path, query string or scan contents, to the resolver. Ordinary successful public system-DNS answers do not trigger that fallback.

This verification does not make an unreachable website reachable. Campus-only access, a disconnected VPN, authentication, a website outage or a bot challenge may still prevent page inspection. It does not change your VPN, proxy or DNS settings.

### Diagnose an address

From the project directory, using the same Python environment as the server:

```bash
python scripts/check_network.py jwxt.zzu.edu.cn
python scripts/check_network.py jwxt.zzu.edu.cn --browser
```

Windows without an activated virtual environment:

```powershell
.\.venv\Scripts\python.exe scripts\check_network.py jwxt.zzu.edu.cn
```

The first command checks target verification. Adding `--browser` runs the real Chromium/axe-core scan and reports the title, engine and findings without writing a database record. This distinguishes a DNS problem from a browser connection, certificate, HTTP or site-access problem.

### Browser proxy connections

Normal VPN/TUN connections require no proxy URL. The browser uses system networking when no proxy environment is configured. In the default `auto` mode, Chromium also inherits `HTTPS_PROXY`, `HTTP_PROXY` or `ALL_PROXY`; Python network requests already support those environment settings.

If your VPN exposes a local HTTP/SOCKS proxy that the browser must use, set its **actual endpoint** in `.env`, for example:

```dotenv
BROWSER_PROXY_URL=http://127.0.0.1:7890
```

The port above is an example, not an assumed VPN port. An explicit URL takes precedence and is also used for HTTPS DNS and GitHub. HTTP proxy authentication is supported. Chromium does not support authenticated SOCKS proxies; use the HTTP endpoint in that case. The saved report records only the route source (`system`, `environment` or `explicit`), never proxy credentials.

Set `BROWSER_PROXY_MODE=system` to stop inheriting proxy environment variables for Chromium. The application does not edit your VPN, system proxy, certificate trust or DNS settings. It never disables TLS verification to force a page to load.

One automatic retry is allowed for selected transient connection errors. HTTP rejection, certificate failures and bot challenges are not retried as a way around access restrictions. Blocked unverifiable subresources are noted as possible missing page content.

## Configuration

Optional settings are loaded from `.env`. New installations can copy `.env.example`.

| Setting | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./accesslens.db` on a fresh installation | Local scan database; legacy filename fallback is described above |
| `SCAN_TIMEOUT_SECONDS` | `45` | Initial navigation timeout; valid range 10–180 seconds |
| `DNS_PUBLIC_FALLBACK` | `true` | Verify public hostnames when DNS is synthetic or unavailable |
| `DNS_HTTPS_TIMEOUT_SECONDS` | `8` | HTTPS-DNS timeout per request; valid range 1–15 seconds |
| `SCREENSHOT_DIR` | Application screenshot directory | Writable screenshot storage location |
| `AXE_JS_PATH` | Bundled `app/engine/vendor/axe.min.js` | Local accessibility engine |
| `BROWSER_PROXY_MODE` | `auto` | Inherit browser proxy environment when present; `system` leaves browser system networking in use |
| `BROWSER_PROXY_URL` | Unset | Optional explicit HTTP/HTTPS/SOCKS5 proxy, also used for DNS and GitHub |

Initial navigation has the configured timeout, with an additional bounded evaluation window for the rest of the scan. DNS-provider requests have their own timeout. Changing settings requires restarting the server.

Turning off `DNS_PUBLIC_FALLBACK` disables the compatibility fallback; it does not enable private-site scanning. It is unnecessary for the reported synthetic-DNS case because the default is already `true`.

## Developer information

The Developer page is fixed to **[MEAZBAH MEHEDI / MeazbahMehedi](https://github.com/MeazbahMehedi)**. Visitors cannot change the account through the website.

GitHub supplies the profile avatar, public name, bio, location, company, website, public email and other available fields. Repository cards show public metadata such as description, topics, language, stars, forks, open issue/PR counts, license, update date and homepage links when supplied.

The service retrieves paginated repository data, supports search/sort in the interface, and shows 12 cards at a time. There is a 2,000-repository safety cap with a visible notice. Responses are cached for ten minutes; outages show an explanatory state or clearly labeled cached data. Empty public repository lists are shown without invented projects. Private repositories and unpublished profile fields are not requested.

## Command line

After installing the project:

```bash
accesslens https://example.com --fail-under 80
accesslens https://example.com --output json
accesslens --help
```

The CLI uses the same scan engine and URL validation. Text output includes coverage notes, findings and review counts. JSON includes structured results. Exit codes are **0** for a completed scan meeting the threshold, **1** for a score below the threshold, and **2** for an invalid option or scan error.

## Docker

```bash
docker compose up --build
```

Open http://127.0.0.1:8000. The Compose configuration uses one application container and an `accesslens-data` volume for SQLite and screenshots. Its published port is bound to localhost. Internet access is required to download images, packages and Chromium, and to reach scanned sites.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| A public hostname resolves to `198.18.x.x`, `198.19.x.x` or `2001:2::…` | Synthetic-DNS compatibility is automatic. Keep `DNS_PUBLIC_FALLBACK=true`, restart the updated application, and run the diagnostic command with `--browser` if scanning still fails. |
| HTTPS DNS verification unavailable | Check internet/VPN/proxy connectivity and whether Google or Cloudflare HTTPS DNS is reachable. TLS and private-target checks remain enabled. |
| Genuine private address rejected | This scanner accepts public pages. A LAN-only or campus-internal target is outside its supported scope. |
| Browser executable missing | Run `python -m playwright install chromium` with the same virtual-environment Python used to start the app. |
| Missing Linux browser library | Run `python -m playwright install --with-deps chromium`. |
| Browser cannot resolve/connect after URL validation passed | Check the browser's actual network/proxy path. Public DNS verification and browser connectivity are separate. |
| Certificate error | Correct the website certificate or the computer's trusted certificate configuration; the scanner does not disable TLS verification. |
| HTTP error, login, consent or challenge page | Inspect the final URL and screenshot. The intended content may require access the automated visitor does not have. |
| Basic checks only | Restore the local engine using `python scripts/fetch_axe.py` and rerun the scan. |
| A scan was interrupted | Restarting the server marks earlier queued/running work failed. Submit a new scan. |
| GitHub information unavailable | Retry later or open the profile link. The page labels stale data and respects unavailable states. |
| Report download error | Inspect the server log and reinstall project dependencies in the active Python environment. Use DOCX for modern Word. |

## Testing

```bash
python -m pytest -q
```

Tests cover public URL validation, IPv4/IPv6 synthetic-DNS compatibility, proxy configuration, resolver fallback and failure behavior, private-address rejection, browser-rendered fixtures, redirect/resource protection, WCAG filtering, result categories, scoring, database upgrades, routes, report exports and GitHub data handling.

Regression tests reproduce the reported `198.18.0.56` and `2001:2::…` cases for the university, ChatGPT and YouTube hostnames without requiring the user's VPN. A full workflow test uses real Chromium and a controlled local proxy to exercise redirects, page resources, persistence and all five report formats. See [validation notes](docs/VALIDATION.md) for checked behavior and environment limits.

## Project layout

```text
AccessLens/
├── app/
│   ├── core/                 # Configuration and public/DNS target verification
│   ├── engine/               # Browser scanner, basic checks and local axe-core
│   ├── services/             # Scoring, reports and GitHub public data
│   ├── web/
│   │   ├── static/           # CSS, JavaScript, icons and runtime screenshots
│   │   └── templates/        # Dedicated workspace pages
│   ├── db.py                 # SQLite models and compatible initialization
│   └── main.py               # Application routes and job lifecycle
├── cli/                      # Command-line scanner
├── docs/                     # Architecture, method, usage and validation
├── scripts/
│   ├── check_network.py      # URL/DNS diagnostic command
│   └── fetch_axe.py          # Restore the pinned engine and upstream license
├── tests/                    # Regression and browser-fixture tests
├── README.md / START_HERE.md / CHANGELOG.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── LICENSE
└── pyproject.toml
```

## Privacy and deployment scope

Scan records and screenshots remain in the configured local database/directories. The application accesses the requested website and its resources. External connections also include GitHub profile/repository data and avatars, and HTTPS DNS when fallback is needed. The bundled engine and local UI assets do not require a runtime CDN.

AccessLens is a **single-user local workspace** with shared local history. It has no authentication, ownership boundaries, distributed queue, scheduler or site-wide crawler. Keep the development server bound to localhost.

URL checks, browser request routing, Chromium redirect interception, blocked service workers and blocked WebSockets provide defense in depth. DNS checks do not pin the actual browser connection to a verified address, and a VPN/proxy controls its own routing. These checks are not a complete SSRF or browser-isolation boundary. Public deployment needs authentication, rate limits, browser sandboxing and enforced outbound-network policy. The current Chromium launch uses `--no-sandbox` for container compatibility.

## Documentation and references

- [User guide](docs/USER_GUIDE.md)
- [Networking and VPN support](docs/NETWORKING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Rules and result interpretation](docs/RULES.md)
- [Validation notes](docs/VALIDATION.md)
- [Future work](docs/NEXT_STEPS.md)
- [Release history](CHANGELOG.md)
- [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [axe-core API documentation](https://www.deque.com/axe/core-documentation/api-documentation/)
- [Mihomo DNS configuration](https://wiki.metacubex.one/en/config/dns/)
- [Google HTTPS-DNS JSON API](https://developers.google.com/speed/public-dns/docs/doh/json)
- [Cloudflare HTTPS-DNS JSON API](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/)

The project includes axe-core **4.10.3**. Restore that pinned bundle and its license with `python scripts/fetch_axe.py` if necessary.

## Contributing

Focused improvements and reproducible bug reports are welcome. Describe the expected behavior, include a safe example or controlled fixture, and run the test suite. Keep automated failures separate from inconclusive checks and recommendations. Do not include credentials, private scan data, a virtual environment or runtime screenshots in a contribution.

If AccessLens is useful to your work, a GitHub star helps others discover it.

## License

Application source is licensed under [MIT](LICENSE). Bundled axe-core is licensed under **Mozilla Public License 2.0**; see its [license](app/engine/vendor/AXE-LICENSE.txt). Dependencies retain their respective licenses.

Maintained by **[MEAZBAH MEHEDI / MeazbahMehedi](https://github.com/MeazbahMehedi)**.
