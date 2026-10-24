import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import pytest
from app.engine import scanner
from app.core.security import UnsafeURLError


@pytest.mark.asyncio
async def test_redirect_and_subresource_private_destinations_blocked(monkeypatch):
    private_hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", f"http://localhost:{self.server.server_port}/private")
                self.end_headers()
                return
            if self.path == "/private":
                private_hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                f'<html lang="en"><head><title>Guard fixture</title></head><body><main><h1>Guard</h1><img alt="" src="http://localhost:{self.server.server_port}/private"></main></body></html>'.encode()
            )

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def safe(url):
        if urlparse(url).hostname != "127.0.0.1":
            raise UnsafeURLError("Blocked fixture destination")
        return url

    monkeypatch.setattr(scanner, "validate_public_url", safe)
    try:
        await scanner.scan_page(f"http://127.0.0.1:{server.server_port}/page")
        assert private_hits == []
        with pytest.raises(Exception):
            await scanner.scan_page(f"http://127.0.0.1:{server.server_port}/redirect")
        assert private_hits == []
    finally:
        server.shutdown()
        server.server_close()
