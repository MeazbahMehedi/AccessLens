"""Reproduce VPN fake-IP DNS without disabling public-target validation."""

import ipaddress
import socket
import httpx
import pytest
from app.core import security


@pytest.fixture(autouse=True)
def reset_dns_cache(monkeypatch):
    security._doh_cache.clear()
    monkeypatch.setattr(security.settings, "dns_public_fallback", True)
    yield
    security._doh_cache.clear()


def system_answers(monkeypatch, values):
    monkeypatch.setattr(
        security, "_resolve_system", lambda host: [security._address(ip) for ip in values]
    )


def doh_transport(monkeypatch, handler):
    real = httpx.Client
    monkeypatch.setattr(
        security.httpx,
        "Client",
        lambda **kwargs: real(**kwargs, transport=httpx.MockTransport(handler), trust_env=False),
    )


def public_response(request, ttl=30):
    record = request.url.params["type"]
    return httpx.Response(
        200,
        json={
            "Status": 0,
            "Answer": [{"type": 1, "data": "59.70.226.18", "TTL": ttl}] if record == "A" else [],
        },
    )


@pytest.mark.parametrize(
    "fake",
    [
        "198.18.0.56",
        "198.19.255.254",
        "::ffff:198.18.0.56",
        "2001:2::a",
        "2001:2::d",
        "2001:2::6",
        "2001:2::e",
    ],
)
def test_university_domain_accepts_verified_public_address_behind_fake_ip(monkeypatch, fake):
    system_answers(monkeypatch, [fake])
    calls = []

    def handler(request):
        calls.append(request.url.params["type"])
        assert request.url.params["name"] == "jwxt.zzu.edu.cn"
        return public_response(request)

    doh_transport(monkeypatch, handler)
    url = "https://jwxt.zzu.edu.cn/login?next=%2Fstudent"
    assert security.validate_public_url(url) == url
    assert sorted(calls) == ["A", "AAAA"]


def test_normal_dns_does_not_contact_public_resolvers(monkeypatch):
    system_answers(monkeypatch, ["8.8.8.8", "2606:4700:4700::1111"])
    monkeypatch.setattr(
        security, "_resolve_public_dns", lambda _: pytest.fail("Unexpected external lookup")
    )
    assert security.validate_public_url("https://example.com") == "https://example.com"


@pytest.mark.parametrize(
    "url",
    [
        "http://[2001:2::d]",
        "http://[2001:2::6]",
        "http://[2001:2::e]",
        "http://198.18.0.56",
        "http://198.19.1.2",
        "http://[::ffff:198.18.0.56]",
        "http://localhost",
        "http://printer.lan",
        "http://service.internal",
        "http://192.168.1.1",
    ],
)
def test_literal_reserved_or_local_target_never_uses_public_fallback(monkeypatch, url):
    monkeypatch.setattr(
        security, "_resolve_public_dns", lambda _: pytest.fail("Private URL must stay blocked")
    )
    with pytest.raises(security.UnsafeURLError):
        security.validate_public_url(url)


@pytest.mark.parametrize(
    "answers",
    [
        ["198.18.0.56", "10.0.0.1"],
        ["2001:2::d", "10.0.0.1"],
        ["198.18.0.56", "2001:2::d", "fc00::1"],
        ["8.8.8.8", "192.168.1.1"],
        ["127.0.0.1"],
        ["169.254.169.254"],
        ["::1"],
        ["fc00::1"],
    ],
)
def test_real_private_system_answer_cannot_be_overridden(monkeypatch, answers):
    system_answers(monkeypatch, answers)
    monkeypatch.setattr(
        security,
        "_resolve_public_dns",
        lambda _: pytest.fail("Real private answers must not be overridden"),
    )
    with pytest.raises(security.UnsafeURLError):
        security.validate_public_url("https://example.com")


@pytest.mark.parametrize(
    "private",
    ["127.0.0.1", "10.1.1.1", "198.18.0.56", "::1", "fc00::1", "::ffff:127.0.0.1", "2001:2::d"],
)
def test_fake_ip_rejected_if_real_dns_has_any_private_family(monkeypatch, private):
    system_answers(monkeypatch, ["198.18.0.56"])
    kind = 28 if ":" in private else 1

    def handler(request):
        record = request.url.params["type"]
        addresses = [{"type": 1, "data": "8.8.8.8", "TTL": 30}] if record == "A" else []
        if (record == "AAAA" and kind == 28) or (record == "A" and kind == 1):
            addresses.append({"type": kind, "data": private, "TTL": 30})
        return httpx.Response(200, json={"Status": 0, "Answer": addresses})

    doh_transport(monkeypatch, handler)
    with pytest.raises(security.UnsafeURLError, match="non-public"):
        security.validate_public_url("https://example.com")


def test_system_dns_failure_uses_verified_https_fallback(monkeypatch):
    monkeypatch.setattr(
        security.socket,
        "getaddrinfo",
        lambda *a, **kw: (_ for _ in ()).throw(socket.gaierror("resolver down")),
    )
    doh_transport(monkeypatch, public_response)
    assert security.validate_public_url("https://example.com") == "https://example.com"


def test_primary_resolver_outage_uses_backup(monkeypatch):
    system_answers(monkeypatch, ["198.18.0.56"])
    providers = []

    def handler(request):
        providers.append(request.url.host)
        if request.url.host == "dns.google":
            raise httpx.ConnectError("offline", request=request)
        return public_response(request)

    doh_transport(monkeypatch, handler)
    security.validate_public_url("https://example.com")
    assert "cloudflare-dns.com" in providers


def test_public_ipv6_only_domain_is_supported(monkeypatch):
    system_answers(monkeypatch, ["198.18.0.56"])
    doh_transport(
        monkeypatch,
        lambda r: httpx.Response(
            200,
            json={
                "Status": 0,
                "Answer": [{"type": 28, "data": "2606:4700:4700::1111", "TTL": 30}]
                if r.url.params["type"] == "AAAA"
                else [],
            },
        ),
    )
    assert security.validate_public_url("https://example.com") == "https://example.com"


def test_incomplete_family_is_not_silently_accepted(monkeypatch):
    system_answers(monkeypatch, ["198.18.0.56"])

    def handler(request):
        if request.url.params["type"] == "AAAA":
            raise httpx.ReadTimeout("offline", request=request)
        return public_response(request)

    doh_transport(monkeypatch, handler)
    with pytest.raises(security.DNSVerificationError, match="synthetic"):
        security.validate_public_url("https://example.com")
    assert not security._doh_cache


def test_private_answer_still_rejected_when_other_family_times_out(monkeypatch):
    system_answers(monkeypatch, ["198.18.0.56"])

    def handler(request):
        if request.url.params["type"] == "A":
            raise httpx.ReadTimeout("offline", request=request)
        return httpx.Response(
            200, json={"Status": 0, "Answer": [{"type": 28, "data": "::1", "TTL": 30}]}
        )

    doh_transport(monkeypatch, handler)
    with pytest.raises(security.UnsafeURLError, match="non-public"):
        security.validate_public_url("https://example.com")


@pytest.mark.parametrize(
    "payload", [{"Status": 2}, {"Status": 0, "TC": True}, {"unexpected": "payload"}]
)
def test_bad_responses_fail_closed_with_connectivity_message(monkeypatch, payload):
    system_answers(monkeypatch, ["198.18.0.56"])
    doh_transport(monkeypatch, lambda r: httpx.Response(200, json=payload))
    with pytest.raises(security.DNSVerificationError, match="could not be verified"):
        security.validate_public_url("https://example.com")


def test_nxdomain_is_not_treated_as_a_public_website(monkeypatch):
    system_answers(monkeypatch, ["198.18.0.56"])
    doh_transport(monkeypatch, lambda r: httpx.Response(200, json={"Status": 3}))
    with pytest.raises(security.UnsafeURLError, match="could not find"):
        security.validate_public_url("https://example.com")


def test_success_cache_respects_ttl_and_avoids_repeat_requests(monkeypatch):
    system_answers(monkeypatch, ["198.18.0.56"])
    calls = []
    clock = [100]
    monkeypatch.setattr(security.time, "monotonic", lambda: clock[0])

    def handler(request):
        calls.append(request.url.params["type"])
        return public_response(request, ttl=10)

    doh_transport(monkeypatch, handler)
    security.validate_public_url("https://example.com/a")
    security.validate_public_url("https://example.com/b")
    assert len(calls) == 2
    clock[0] = 111
    security.validate_public_url("https://example.com")
    assert len(calls) == 4


def test_disabling_fallback_gives_actionable_error(monkeypatch):
    system_answers(monkeypatch, ["198.18.0.56"])
    monkeypatch.setattr(security.settings, "dns_public_fallback", False)
    with pytest.raises(security.DNSVerificationError, match="DNS_PUBLIC_FALLBACK"):
        security.validate_public_url("https://example.com")


@pytest.mark.asyncio
async def test_verified_fake_ip_hostname_reaches_real_rendered_engine(monkeypatch):
    from urllib.parse import urlparse
    from playwright.async_api import Route
    from app.engine.scanner import scan_page

    system_answers(monkeypatch, ["198.18.0.56"])
    doh_transport(monkeypatch, public_response)
    original_continue = Route.continue_
    html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Public DNS fixture</title></head><body><main><h1>Accessible fixture</h1><p>The hostname remained intact.</p></main></body></html>'

    async def serve_fixture(route, *args, **kwargs):
        if urlparse(route.request.url).hostname == "public-site.example":
            await route.fulfill(status=200, content_type="text/html", body=html)
        else:
            await original_continue(route, *args, **kwargs)

    monkeypatch.setattr(Route, "continue_", serve_fixture)
    result = await scan_page("https://public-site.example")
    assert result.title == "Public DNS fixture"
    assert result.url == "https://public-site.example/"
    assert result.metadata["coverage"] == "axe"
    assert result.findings == []


@pytest.mark.parametrize(
    "host,fake",
    [
        ("jwxt.zzu.edu.cn", "2001:2::d"),
        ("chatgpt.com", "2001:2::6"),
        ("youtube.com", "2001:2::e"),
        ("www.zzu.edu.cn", "2001:2::a"),
    ],
)
@pytest.mark.parametrize("with_ipv4", [False, True])
def test_reported_hosts_with_ipv6_or_dual_stack_synthetic_dns(monkeypatch, host, fake, with_ipv4):
    answers = [fake] + (["198.18.0.56"] if with_ipv4 else [])
    system_answers(monkeypatch, answers)
    doh_transport(monkeypatch, public_response)
    url = f"https://{host}/"
    assert security.validate_public_url(url) == url


def test_synthetic_ipv6_plus_real_public_ipv4_still_verifies_independently(monkeypatch):
    system_answers(monkeypatch, ["8.8.8.8", "2001:2::e"])
    calls = []

    def lookup(host):
        calls.append(host)
        return security.DNSAnswer((ipaddress.ip_address("8.8.8.8"),))

    monkeypatch.setattr(security, "_resolve_public_dns", lookup)
    security.validate_public_url("https://youtube.com")
    assert calls == ["youtube.com"]
