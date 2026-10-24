from datetime import datetime, timezone
import asyncio
import pytest
from fastapi.testclient import TestClient
from app import main
from app.db import SessionLocal, Scan


async def seed():
    async with SessionLocal() as db:
        for id, status in [("route-done", "done"), ("route-failed", "failed")]:
            if not await db.get(Scan, id):
                db.add(
                    Scan(
                        id=id,
                        url="https://example.com",
                        title="Test page",
                        status=status,
                        score=93,
                        scan_metadata={"scoring_version": "2", "coverage": "axe"},
                        issues=[
                            {
                                "rule_id": "label",
                                "impact": "serious",
                                "message": "Missing name",
                                "source": "axe-core",
                                "category": "violation",
                                "wcag_criteria": ["4.1.2"],
                            }
                        ],
                        issue_count=1,
                        serious_count=1,
                        review_items=[],
                    )
                )
        await db.commit()


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        c.portal.call(seed)
        yield c


@pytest.mark.parametrize(
    "url",
    [
        "/",
        "/dashboard",
        "/new-scan",
        "/history",
        "/reports",
        "/developer",
        "/about",
        "/scan/route-done",
        "/scan/route-failed",
    ],
)
def test_pages_render(client, url):
    r = client.get(url)
    assert r.status_code == 200
    assert "<main" in r.text
    assert 'href="/docs"' not in r.text


@pytest.mark.parametrize("url", ["/docs", "/redoc", "/openapi.json", "/scan/not-found"])
def test_removed_api_page_and_missing_scan(client, url):
    assert client.get(url).status_code == 404


@pytest.mark.parametrize(
    "fmt,mime",
    [
        ("pdf", "application/pdf"),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("doc", "application/msword"),
        ("csv", "text/csv"),
        ("json", "application/json"),
    ],
)
def test_download_routes(client, fmt, mime):
    r = client.get("/scan/route-done/export", params={"format": fmt})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(mime)
    assert "attachment;" in r.headers["content-disposition"]
    assert len(r.content) > 100


def test_export_blocks_incomplete(client):
    assert client.get("/scan/route-failed/export").status_code == 409


def test_export_rejects_bad_format(client):
    assert client.get("/scan/route-done/export?format=exe").status_code == 400


def test_private_url_and_level_validation(client):
    assert (
        client.post("/scan", data={"url": "http://127.0.0.1", "wcag_level": "AA"}).status_code
        == 422
    )
    assert (
        client.post(
            "/scan", data={"url": "https://example.com", "wcag_level": "INVALID"}
        ).status_code
        == 422
    )


def test_dashboard_data_excludes_failed_and_legacy(client):
    data = client.get("/internal/dashboard").json()
    assert data["completed"] == 1
    assert data["avg"] == 93


def test_history_filters(client):
    text = client.get("/history?status=failed").text
    assert "route-failed" in text
    assert "route-done" not in text


def test_scan_submission_completes_and_exports(client, monkeypatch):
    import time
    from app.engine.scanner import PageResult, Finding

    monkeypatch.setattr(main, "validate_public_url", lambda url: url)

    async def fake_scan(*args):
        return PageResult(
            "https://example.com",
            "Rendered fixture",
            12,
            [Finding("label", "serious", "A label is missing.")],
            metadata={"coverage": "axe", "scoring_version": "2"},
        )

    monkeypatch.setattr(main, "scan_page_isolated", fake_scan)
    r = client.post(
        "/scan", data={"url": "example.com", "wcag_level": "AA"}, follow_redirects=False
    )
    assert r.status_code == 303
    id = r.headers["location"].split("/")[-1]
    for _ in range(100):
        if client.get(f"/internal/scans/{id}/status").json()["status"] == "done":
            break
        time.sleep(0.02)
    d = client.get(f"/scan/{id}/export?format=json")
    assert d.status_code == 200
    assert d.json()["score"] == 93
    assert d.json()["issue_count"] == 1


def test_fake_ip_dns_is_accepted_by_scan_submission(client, monkeypatch):
    import ipaddress
    from app.core import security
    from app.engine.scanner import PageResult

    monkeypatch.setattr(
        security, "_resolve_system", lambda host: [ipaddress.ip_address("198.18.0.56")]
    )
    monkeypatch.setattr(
        security,
        "_resolve_public_dns",
        lambda host: security.DNSAnswer((ipaddress.ip_address("59.70.226.18"),)),
    )

    async def fake_scan(*args):
        return PageResult(
            "https://jwxt.zzu.edu.cn",
            "University fixture",
            1,
            [],
            metadata={"scoring_version": "2", "coverage": "axe"},
        )

    monkeypatch.setattr(main, "scan_page_isolated", fake_scan)
    response = client.post(
        "/scan", data={"url": "jwxt.zzu.edu.cn", "wcag_level": "AA"}, follow_redirects=False
    )
    assert response.status_code == 303
    # Complete the background write before this test client tears down its loop.
    import time

    scan_id = response.headers["location"].split("/")[-1]
    for _ in range(100):
        status = client.get(f"/internal/scans/{scan_id}/status").json()["status"]
        if status == "done":
            break
        time.sleep(0.02)
    assert status == "done"


def test_dns_outage_is_reported_as_service_unavailable(client, monkeypatch):
    from app.core.security import DNSVerificationError

    def fail(url):
        raise DNSVerificationError(
            "Public DNS could not be verified. Check VPN/proxy connectivity."
        )

    monkeypatch.setattr(main, "validate_public_url", fail)
    response = client.post("/scan", data={"url": "example.com", "wcag_level": "AA"})
    assert response.status_code == 503
    assert "Check VPN/proxy connectivity" in response.text
