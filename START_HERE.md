# Start the fixed version

This package is AccessLens **2.0.2**. It recognizes the reported VPN synthetic IPv4 and IPv6 addresses, including `2001:2::d`, `2001:2::6` and `2001:2::e`.

1. Stop the previous server with **Ctrl+C**.
2. Extract this ZIP into a fresh folder. Keep a backup of your previous database, screenshots and `.env` if you need your history.
3. Follow the Windows or macOS/Linux setup in README. Use the virtual-environment Python to install dependencies, install Chromium and start the application.
4. Open `http://127.0.0.1:8000/health`. The returned version must be **2.0.2**. If it is older, stop that server and launch from this extracted project.
5. Open **New scan** and submit the website again. Old failed records remain historical records.

A normal VPN/TUN connection requires no proxy URL. If your VPN requires an explicit local HTTP/SOCKS endpoint, configure its actual address in `BROWSER_PROXY_URL`; see README. Do not copy an example port unless it matches your VPN client.

To test the full browser path without saving a record:

```bash
python scripts/check_network.py jwxt.zzu.edu.cn --browser
```

This version passed 141 regression tests, including a real Chromium/proxy/redirect/resource/database/export workflow. Third-party login requirements, inaccessible servers, untrusted certificates and anti-bot challenges can still prevent a page from being audited; failures are explained rather than assigned a misleading accessibility score.
