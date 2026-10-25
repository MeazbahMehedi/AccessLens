"""Exercise real Chromium, redirect/resources, database persistence and all exports.

Only the DNS service and the local HTTP proxy are fixture-controlled; production URL
validation, scan jobs, axe-core and export implementations remain enabled.
"""

import ipaddress
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from fastapi.testclient import TestClient
import httpx
from pydantic import SecretStr
from urllib.parse import urlsplit
from app import main
from app.core import security


def test_dual_stack_vpn_scan_redirect_resources_persistence_and_exports(monkeypatch):
    security._doh_cache.clear()
    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            hits.append((self.headers.get("Host"), path))
            if path == "/start":
                self.send_response(302)
                self.send_header("Location", "http://www.zzu.edu.cn/audit")
                self.end_headers()
                return
            self.send_response(200)
            if path == "/style.css":
                self.send_header("Content-Type", "text/css")
                self.end_headers()
                self.wfile.write(b"button { min-width:44px; min-height:44px; margin:16px }")
                return
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"""<!doctype html><html lang="en"><head><title>VPN workflow fixture</title><link rel="stylesheet" href="http://static.accesslens.test/style.css"></head><body><main><h1>Controlled accessibility audit</h1><button></button><p>Public hostname preserved through redirects.</p></main></body></html>""".encode()
            )

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(
        security,
        "_resolve_system",
        lambda host: [ipaddress.ip_address("198.18.0.56"), ipaddress.ip_address("2001:2::d")],
    )
    real_client = httpx.Client

    def dns(request):
        return httpx.Response(
            200,
            json={
                "Status": 0,
                "Answer": [{"type": 1, "data": "8.8.8.8", "TTL": 30}]
                if request.url.params["type"] == "A"
                else [{"type": 28, "data": "2606:4700:4700::1111", "TTL": 30}],
            },
        )

    proxy_url = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setattr(security.settings, "browser_proxy_url", SecretStr(proxy_url))

    def dns_client(**kwargs):
        assert kwargs.pop("proxy") == proxy_url
        return real_client(**kwargs, transport=httpx.MockTransport(dns), trust_env=False)

    monkeypatch.setattr(security.httpx, "Client", dns_client)
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/scan",
                data={
                    "url": "http://jwxt.zzu.edu.cn/start",
                    "wcag_level": "AA",
                },
                follow_redirects=False,
            )
            assert response.status_code == 303, response.text
            scan_id = response.headers["location"].split("/")[-1]
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                status = client.get(f"/internal/scans/{scan_id}/status").json()
                if status["status"] in {"done", "failed"}:
                    break
                time.sleep(0.05)
            assert status["status"] == "done", (status, hits)
            data = client.get(f"/scan/{scan_id}/export?format=json").json()
            assert data["title"] == "VPN workflow fixture"
            assert data["metadata"]["final_url"] == "http://www.zzu.edu.cn/audit"
            assert data["metadata"]["coverage"] == "axe"
            assert any(i["rule_id"] == "button-name" for i in data["issues"])
            assert client.get(f"/scan/{scan_id}").status_code == 200
            for fmt, signature in [
                ("pdf", b"%PDF"),
                ("docx", b"PK"),
                ("doc", b"{\\rtf1"),
                ("csv", b"\xef\xbb\xbf"),
            ]:
                download = client.get(f"/scan/{scan_id}/export?format={fmt}")
                assert download.status_code == 200, (fmt, download.text[:200])
                assert download.content.startswith(signature), fmt
            assert any(
                host == "static.accesslens.test" and path == "/style.css" for host, path in hits
            )
    finally:
        server.shutdown()
        server.server_close()
        security._doh_cache.clear()
