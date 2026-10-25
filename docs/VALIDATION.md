# Release validation

## AccessLens branding verification — 25 October 2026

The project/root folder, installed CLI, app and report labels, documentation, logo/favicon asset and report download filenames were renamed. The supplied scanner, axe-core bundle/license, basic checks, scoring, storage, network/DNS logic and CSS retain their behavior; changes in those modules are limited to project-name references.

- Full regression suite: **141 passed** on Python 3.12, including real Chromium fixtures, VPN/DNS handling and five-format report downloads. The installed FastAPI/Starlette test client emitted one dependency deprecation warning.
- CLI installation and help output succeeded with the new `accesslens` command.
- Browser checks exercised seven rendered pages in light/dark themes at 1440-pixel and 390-pixel widths, including the new title/logo, theme persistence, legacy theme fallback and mobile navigation; no JavaScript exceptions were observed.
- The 28 page/viewport/theme width measurements matched the original application. This comparison preserves the original responsive behavior, including its existing overflow where present.
- All five export endpoints produced the renamed attachment filenames. PDF and Word report contents carried the updated branding. The Word/PDF sample reports were rendered for visual review.
- Configuration checks confirmed the fresh database filename, legacy database selection without changing saved data, and precedence of an explicitly configured database URL.

The original release evidence below retains its original scope. This branding update did not repeat live university/public-site connectivity checks, native Windows/macOS execution or a Docker image build.

## Original release evidence

This release was checked in a Linux environment with Python 3.12 and Playwright Chromium. The regression suite contains **141 passing tests**.

## DNS compatibility verification

- Reproduced `198.18.0.56` and the reported IPv6 substitutes `2001:2::a`, `2001:2::d`, `2001:2::6` and `2001:2::e`. Verified IPv6-only, mixed synthetic A/AAAA and synthetic-plus-real-public answers for university, ChatGPT and YouTube hostnames.
- Checked IPv4/IPv6, mixed private/public records, literal reserved addresses, local names, resolver failure/failover, malformed responses, NXDOMAIN, TTL-bound caching and compatibility-disabled behavior.
- A browser-rendered fixture retains its original HTTPS hostname and runs the real axe-core engine after synthetic-DNS verification. Only the fixture's network response is supplied by the test; public-target validation remains enabled.
- Scan submission accepts the synthetic-DNS/public-hostname case; resolver outages return a clear 503 connection error.
- Live HTTPS DNS returned the public IPv4 address `59.70.226.18` for `jwxt.zzu.edu.cn`, with no AAAA answer. One resolver timed out during verification; the other resolver succeeded. The fallback is therefore a real provider failover path, not an unconditional allow rule.
- With the reported synthetic IPv4/IPv6 OS answers supplied, live HTTPS DNS verification accepted `jwxt.zzu.edu.cn`, `chatgpt.com` and `youtube.com` using real public resolver responses.
- A complete workflow test uses real Chromium, a controlled local HTTP proxy, real redirects and stylesheet loads, the actual axe-core engine, SQLite persistence and PDF/DOCX/DOC/CSV/JSON downloads. Production target validation remains enabled; DNS answers and the fixture proxy content are controlled for the test.
- Proxy configuration tests cover environment inheritance, explicit endpoints, HTTP authentication, SOCKS translation, credential-safe errors and system-networking mode. Browser failures distinguish DNS, proxy, certificate, timeout and HTTP/page-access errors. Only selected transient connection failures qualify for one retry.
- A live HTTPS browser attempt for example.com reached the configured proxy path but was stopped by certificate verification in this execution environment. TLS verification was not disabled. The user's actual VPN route and protected websites were not validated end to end. No claim is made that DNS verification guarantees browser connectivity, trusted certificates or university login access.

## Verified behavior

- All workspace page routes render, including completed/failed reports.
- API documentation/OpenAPI routes are removed.
- Private/local URL inputs and malformed targets are rejected; mixed public/private DNS records are rejected.
- Controlled browser fixtures check clean content, broken titles/language/images/forms/buttons, hidden elements and valid ARIA references.
- WCAG A/AA filtering, success-criterion parsing, deduplication, incomplete review items and best-practice exclusion are tested.
- HTTP 404 and recognizable challenge pages fail rather than produce a score.
- A browser-level fixture verifies that private subresources and a private redirect destination are **not contacted**. Chromium response interception validates redirect Location headers before following them; ordinary Playwright routing alone was insufficient.
- Rule-capped scoring, severity weighting and principle scores are checked.
- Existing SQLite records survive the additive review/metadata-column migration.
- Scan submission, background completion and JSON export are exercised through FastAPI's test client.
- PDF, DOCX, DOC/RTF, CSV and JSON downloads return the appropriate content type and attachment headers; unfinished/failed scans cannot export.
- PDF and DOCX contents are parsed; multipage PDF generation, extra CSV fields, empty reports and spreadsheet formula protection are checked.
- GitHub public-profile retrieval, multi-page repository retrieval, caching, unavailable-state behavior and stale fallback are checked with controlled responses.
- A live request successfully returned the fixed developer's public GitHub profile. At validation time, GitHub returned zero public repositories; no repository cards were fabricated.
- An installable 2.0.2 wheel was built, and required templates, styles, scanner JavaScript, axe-core and its license were confirmed in the package.

## Visual verification

Desktop page snapshots from the real Jinja2 templates were reviewed in Chrome, including the Overview, New Scan, Developer, History and report pages. Both themes, finding search and expandable evidence were inspected. Snapshot evidence came from a controlled browser-scanned fixture.

The managed preview environment does not expose the Python application runtime, so visual QA used prerendered pages. Backend request/job/export behavior was verified separately through the real application test client and scanner. Responsive CSS and a mobile navigation menu are included; mobile-device visual testing was not performed.

## Limits

Windows and macOS were not run in this environment. The Windows-specific event-loop path is retained, and PDF generation no longer needs WeasyPrint native libraries. Docker configuration was corrected to match the application, but an image build was not executed here.

Public website output varies by region, time, consent state, account, page content and automation restrictions. Controlled tests cannot certify the results for every website. The scan engine, heuristic score and generated PDF/DOCX reports are not accessibility-compliance certifications. The PDF output is not a tagged accessible PDF.

A dependency deprecation warning from the installed FastAPI/Starlette test client was observed; it did not cause test failures. Dependency versions are declared as compatible ranges rather than a fully locked environment.
