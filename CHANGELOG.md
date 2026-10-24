# Changes

## 2.0.2 — IPv6 VPN DNS and browser connectivity

- Recognize the reported `2001:2::/48` synthetic IPv6 range as well as `198.18.0.0/15` IPv4, including mixed answers.
- Use the shared verification path for submissions, navigation, redirects, final URLs and resources. Literal reserved IPs and genuine private targets remain rejected.
- Let Chromium inherit proxy environment settings, with an optional explicit proxy shared by browser, DNS and GitHub.
- Add actionable browser DNS, proxy, TLS, timeout and page-access errors, structured failure metadata and one bounded transient-connection retry.
- Add a browser diagnostic option and full Chromium/proxy/redirect/resource/database/export regression coverage.
- Update whole-program documentation and version-check instructions.

## 2.0.1 — Public website DNS compatibility

- Recognize VPN/proxy synthetic DNS answers in 198.18.0.0/15 for hostnames.
- Independently verify A and AAAA records over HTTPS before accepting those public hostnames.
- Fall back to HTTPS DNS when system DNS is unavailable, with provider failover and short TTL-bound caching.
- Continue rejecting literal reserved IPs, real private DNS answers and unverified targets.
- Report DNS-verification outages as connectivity errors rather than falsely declaring a public website private.
- Reuse pending destination checks inside a scan to avoid duplicate lookups for concurrent resources.
- Add a network diagnostic command and synthetic-DNS/browser regression coverage.
- Rewrite README as documentation for the complete program.

## 2.0.0 — Workspace and accuracy update

### Interface

- Added dedicated Overview, New Scan, Scan History, Reports, Developer and About pages.
- Rebuilt the visual system, navigation, mobile layout, dark/light themes and loading/error/empty states.
- Added charts based on persisted results, report search and finding-category/severity filters.
- Removed the API documentation page and its navigation entry.

### Scanner and interpretation

- Separated WCAG failures from best practices and incomplete manual-review results.
- Applied cumulative WCAG target tags at axe execution and result parsing.
- Removed blanket custom target-size and vague-link assertions; corrected hidden-element and accessible-name handling in basic coverage.
- Added explicit engine, coverage, final URL, HTTP status and timing metadata.
- Introduced rule-capped heuristic scoring version 2 and excluded legacy scores from current aggregates.
- Rejected HTTP error/challenge pages; made screenshot failure non-fatal.
- Checked redirect/resource destinations before browser requests and bounded queue/scan work.

### Reports and developer

- Fixed CSV export failures caused by extra finding fields; added UTF-8 BOM and spreadsheet formula protection.
- Replaced native PDF dependencies with ReportLab.
- Added editable DOCX and Word-compatible legacy DOC/RTF exports.
- Added completion guards and visible download error handling.
- Added fixed read-only public GitHub profile/repositories with pagination, caching, sorting and outage states.

### Project

- Bundled pinned axe-core and upstream license.
- Added compatible SQLite schema upgrade for existing records.
- Simplified Docker to match the real application architecture.
- Updated README, usage, architecture, rules and validation documentation.
- Added rendered-fixture, export, route, scoring, security and GitHub regression tests.
