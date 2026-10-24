# User guide

1. Follow the platform setup in README. Open http://127.0.0.1:8000.
2. Choose **New scan**. Enter a public page URL and select A, AA or AAA. AA is the default.
3. Start the scan. You are redirected to a status page. Results update automatically; the scan can also be reopened from History.
4. Read coverage notes first. Confirm that the captured page and final URL are the page you intended to audit.
5. Inspect the score, severity counts and principle scores. Scores are heuristic indicators, not WCAG compliance percentages.
6. Open **Confirmed findings**, search or filter by severity, and expand a finding to see selector, HTML evidence and remediation.
7. Open **Review & best practices** for inconclusive checks and unscored recommendations.
8. Expand the captured screenshot. Red outlines identify located failing elements. Some frame/shadow targets cannot be highlighted.
9. Download PDF, Word, DOC, CSV or JSON from the report header or Reports page. Failed or unfinished scans cannot be exported.
10. Use History search/status filters to find a previous scan. The Overview summarizes current-engine completed results; legacy records are retained but excluded from those metrics.
11. Visit Developer for live public GitHub details. The developer identity is fixed in code. Empty public repository lists are shown honestly, and unavailable GitHub data produces an explanatory state.
12. Use the theme button for dark/light appearance. On narrow screens, the menu button opens navigation; Escape closes it.

Confirm `/health` reports version **2.0.2** after installing this release. Submit a fresh scan; a historical failed report does not rerun itself.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| Browser executable missing | Run `python -m playwright install chromium` using the same virtual-environment Python as the server. |
| Missing Linux browser library | Run `python -m playwright install --with-deps chromium`. |
| URL rejected | Use HTTP/HTTPS, no credentials or control characters, and a public destination. Real local/private addresses are intentionally blocked. Public hostnames behind recognized VPN synthetic DNS are independently verified. |
| DNS returns 198.18.x.x / 198.19.x.x / 2001:2::… | Public-hostname compatibility is automatic with `DNS_PUBLIC_FALLBACK=true`. Restart the updated server. Run `python scripts/check_network.py jwxt.zzu.edu.cn --browser` to test validation and actual page inspection. |
| HTTPS DNS verification unavailable | Check VPN/proxy connectivity and reachability of Google or Cloudflare HTTPS DNS. The default timeout is eight seconds per request; increase `DNS_HTTPS_TIMEOUT_SECONDS` up to 15 if needed. |
| HTTP error or challenge | The intended page was not audited. Try a permitted, reachable page. Do not interpret the failed attempt as a low accessibility score. |
| Basic-checks notice | Restore the bundled script with `python scripts/fetch_axe.py`, then scan again. |
| Legacy report | Run the page again with version 2. Existing scores cannot be compared directly with the corrected method. |
| Stuck after restart | Startup marks interrupted jobs failed. Create a new scan. |
| GitHub unavailable | Wait for the retry window or visit the profile link directly. Cached data is labeled when stale. |
| No public repositories | GitHub currently has no public repositories available for that account. New public repositories appear on the next successful refresh. |
| Export error | Check the terminal for the logged error and reinstall project dependencies in the active environment. Modern Word uses the DOCX option. |

Use a single local server worker. Keep the development server private; this application has no account system.
