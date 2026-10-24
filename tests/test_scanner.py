from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from app.engine import scanner

NODE = {"target": ["#a"], "html": '<a id="a"></a>', "failureSummary": "Add text"}


def rule(tags, id="link-name"):
    return {"id": id, "impact": "serious", "tags": tags, "nodes": [NODE], "help": "Name is missing"}


def test_wcag_level_and_review_separation():
    data = {
        "violations": [
            rule(["wcag2a", "wcag244"]),
            rule(["best-practice"], "landmark-one-main"),
            rule(["wcag22aa", "wcag258"], "target-size"),
        ],
        "incomplete": [rule(["wcag2aa", "wcag143"], "color-contrast")],
    }
    issues, reviews = scanner.axe_findings(data, "A")
    assert [i["rule_id"] for i in issues] == ["link-name"]
    assert len(reviews) == 1
    assert reviews[0]["category"] == "best-practice"
    issues, reviews = scanner.axe_findings(data, "AA")
    assert len(issues) == 2
    assert len(reviews) == 2
    assert reviews[1]["category"] == "review"


def test_criteria_and_dedup():
    r = rule(["wcag2a", "wcag2411"])
    r["nodes"] = [NODE, NODE]
    issues, _ = scanner.axe_findings({"violations": [r]})
    assert len(issues) == 1
    assert issues[0]["wcag_criteria"] == ["2.4.11"]


def test_challenge_not_article_false_positive():
    assert scanner._detect_challenge("Just a moment...", "Checking browser")
    assert not scanner._detect_challenge(
        "Bot detection explained", "A long article. " * 500 + "Verify you are human"
    )


@pytest.fixture
def fixture_site():
    pages = {
        "/clean": '<!doctype html><html lang="en"><head><title>Clean fixture</title></head><body><main><h1>Clean</h1><p>Accessible content.</p><label for="name">Name</label><input id="name"><button>Save</button><a href="/clean">Home</a></main></body></html>',
        "/broken": '<!doctype html><html><head><title></title></head><body><img src="data:image/gif;base64,R0lGODlhAQABAAAAACw="><input><button></button></body></html>',
        "/hidden": '<!doctype html><html lang="en"><head><title>Valid names</title><style>button,input{min-height:44px;min-width:44px;margin:14px}</style></head><body><main><h1>Form</h1><div hidden><input><button></button><img src="none"></div><span id="label">User name</span><input aria-labelledby="label"><button aria-label="Close"></button><p>Read <a href="/clean">more</a> about this topic.</p></main></body></html>',
        "/challenge": "<html><head><title>Just a moment...</title></head><body>Verify you are human</body></html>",
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(404 if self.path == "/missing" else 200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(pages.get(self.path, "Not found").encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_rendered_checks_and_basic_fallback(monkeypatch, fixture_site, tmp_path):
    monkeypatch.setattr(
        scanner, "validate_public_url", lambda url: url
    )  # Controlled local fixtures only.
    result = await scanner.scan_page(fixture_site + "/broken", str(tmp_path / "shot.png"))
    assert result.metadata["coverage"] == "axe"
    assert {"document-title", "html-has-lang", "image-alt", "label", "button-name"} <= {
        i.rule_id for i in result.findings
    }
    assert Path(result.screenshot_path).is_file()
    clean = await scanner.scan_page(fixture_site + "/clean")
    assert not clean.findings
    hidden = await scanner.scan_page(fixture_site + "/hidden")
    assert not hidden.findings
    monkeypatch.setattr(scanner.settings, "axe_js_path", str(tmp_path / "missing.js"))
    basic = await scanner.scan_page(fixture_site + "/hidden")
    assert not basic.findings
    assert basic.metadata["coverage"] == "basic"
    assert not any(i.rule_id == "target-size" for i in basic.findings)


@pytest.mark.asyncio
@pytest.mark.parametrize("path,match", [("/missing", "HTTP 404"), ("/challenge", "anti-bot")])
async def test_blocked_pages_not_scored(monkeypatch, fixture_site, path, match):
    monkeypatch.setattr(scanner, "validate_public_url", lambda url: url)
    with pytest.raises(RuntimeError, match=match):
        await scanner.scan_page(fixture_site + path)
