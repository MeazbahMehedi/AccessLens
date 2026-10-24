import ipaddress
import pytest
from app.core import security


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "file:///etc/passwd",
        "localhost",
        "http://127.0.0.1",
        "http://10.0.0.5",
        "http://[::1]",
        "http://[::ffff:127.0.0.1]",
        "http://224.0.0.1",
        "http://user:pass@example.com",
        "https://example.com:bad",
        "https://example.com/a\nb",
        "http://test.local",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(security.UnsafeURLError):
        security.validate_public_url(url)


def test_requires_http_scheme():
    with pytest.raises(security.UnsafeURLError):
        security.validate_public_url("example.com")


def test_mixed_private_and_public_dns_rejected(monkeypatch):
    monkeypatch.setattr(
        security,
        "_resolve_system",
        lambda host: [ipaddress.ip_address("8.8.8.8"), ipaddress.ip_address("192.168.1.4")],
    )
    with pytest.raises(security.UnsafeURLError):
        security.validate_public_url("https://example.com")


def test_public_domain_and_normalization(monkeypatch):
    monkeypatch.setattr(security, "_resolve_system", lambda host: [ipaddress.ip_address("8.8.8.8")])
    assert (
        security.validate_public_url(security.normalize_url(" example.com "))
        == "https://example.com"
    )
