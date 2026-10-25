# Website access and VPN support

AccessLens scans public HTTP/HTTPS pages. Website address eligibility and the browser's ability to load content are separate steps, and both are checked.

## Synthetic DNS, both address families

A VPN/proxy can substitute benchmark-range addresses for public names. The recognized system-DNS substitutes are:

| Family | Range | Example |
| --- | --- | --- |
| IPv4 | `198.18.0.0/15` | `198.18.0.56` |
| IPv6 | `2001:2::/48` | `2001:2::d` |

The same logic applies to the initial submitted URL, navigation requests, redirects, final captured URL and page resources. An IPv6-only substitute and a mixed IPv4/IPv6 substitute both trigger independent verification of the hostname's public A and AAAA records over HTTPS. Verification is not a host allowlist; university, ChatGPT and YouTube names are regression examples, not hard-coded exceptions.

A literal reserved IP URL stays blocked. A real private address in system or public DNS is not ignored merely because another record is public or synthetic. Unrecognized private IPv6 ranges such as `fc00::/7` remain blocked. Verification failure produces a connection/DNS error, rather than an accessibility score.

Only successful public HTTPS-DNS results are cached, for at most their address-record TTL or 60 seconds. The browser retains the original hostname for normal HTTPS/SNI and VPN routing. This is public-host verification, not a guarantee about the proxy's eventual network destination.

## Browser route

- With no proxy configuration, normal system/VPN/TUN networking is used.
- `BROWSER_PROXY_MODE=auto` lets Chromium inherit proxy environment settings.
- `BROWSER_PROXY_URL` explicitly selects a proxy endpoint and also applies to HTTPS DNS and GitHub.
- `BROWSER_PROXY_MODE=system` suppresses environment inheritance for Chromium; an explicit URL still takes precedence.
- HTTP/HTTPS proxy credentials are parsed separately from the server URL. Authenticated SOCKS is rejected with a clear configuration message because Chromium cannot use it.

No credentials are stored in scan metadata or printed by the diagnostic command. Only the route source is stored.

The project does not change the VPN or proxy service. If using a local proxy endpoint, get its real port from that client; a documentation example is not a guaranteed port number.

## Test the complete scan

Use the same Python environment as the application:

```bash
python scripts/check_network.py jwxt.zzu.edu.cn --browser
```

Without `--browser`, the command only checks DNS/URL eligibility. With it, the command loads the page and runs the actual engine without saving a database record.

## Failure categories

| Error | Interpretation |
| --- | --- |
| Public DNS verification unavailable | The real public destination could not be verified over HTTPS DNS. |
| Browser DNS error | Verification passed, but Chromium's network route cannot resolve the destination. |
| Proxy connection/configuration error | The endpoint, authentication or proxy service needs attention. |
| Certificate error | The website/proxy certificate is not trusted; verification remains enabled. |
| Connection timeout/reset/empty response | The browser could not establish or complete the page connection. One selected transient error may be retried. |
| HTTP rejection / recognizable challenge | The intended content was not available to the automated visitor. No accessibility score is generated for it. |
| Blocked resource note | Some unverifiable resources were blocked; the resulting page may be incomplete. |

An empty response or bare HTTP status is not automatically labeled bot detection. The application does not solve challenges, log in, bypass access controls or suppress TLS verification. No application can guarantee access to every third-party website or every private/campus-only page.

## Confirm the updated code is running

Stop the previous server, update/install the source and restart it. Visit `/health` and check `version: 2.0.2`. Old failed records remain historical records; submit a fresh scan to test the updated engine.
