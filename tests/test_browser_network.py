"""Networking behavior, not just URL-validator return values."""

import pytest
from pydantic import SecretStr
from app.core import network


@pytest.fixture(autouse=True)
def clean_proxy(monkeypatch):
    monkeypatch.setattr(network.settings, "browser_proxy_url", None)
    monkeypatch.setattr(network.settings, "browser_proxy_mode", "auto")
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(key, raising=False)


def test_default_uses_system_route_without_environment_proxy():
    assert network.browser_proxy_options() == (None, "system")


def test_browser_inherits_https_proxy_environment(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
    assert network.browser_proxy_options() == ({"server": "http://127.0.0.1:7890"}, "environment")


def test_explicit_proxy_overrides_environment_and_preserves_credentials(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9999")
    monkeypatch.setattr(
        network.settings, "browser_proxy_url", SecretStr("http://user:p%40ss@127.0.0.1:7890")
    )
    options, source = network.browser_proxy_options()
    assert options == {"server": "http://127.0.0.1:7890", "username": "user", "password": "p@ss"}
    assert source == "explicit"
    assert network.httpx_proxy_options()["proxy"].startswith("http://user:")


def test_socks5h_is_translated_for_chromium(monkeypatch):
    monkeypatch.setenv("ALL_PROXY", "socks5h://127.0.0.1:7891")
    assert network.browser_proxy_options() == ({"server": "socks5://127.0.0.1:7891"}, "environment")


def test_system_mode_does_not_inherit_proxy_environment(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setattr(network.settings, "browser_proxy_mode", "system")
    assert network.browser_proxy_options() == (None, "system")


@pytest.mark.parametrize(
    "value",
    [
        "http://secret:password@proxy.invalid:not-a-port",
        "ftp://secret:password@proxy.invalid:21",
        "not-a-proxy",
        "http://proxy.invalid:80/a?token=secret",
    ],
)
def test_invalid_proxy_has_actionable_error_without_secrets(monkeypatch, value):
    monkeypatch.setattr(network.settings, "browser_proxy_url", SecretStr(value))
    with pytest.raises(network.ScanFailure) as info:
        network.browser_proxy_options()
    assert info.value.code == "proxy_configuration"
    assert "secret" not in str(info.value)
    assert "password" not in str(info.value)


def test_authenticated_socks_has_clear_unsupported_message(monkeypatch):
    monkeypatch.setattr(
        network.settings, "browser_proxy_url", SecretStr("socks5://secret:password@127.0.0.1:7891")
    )
    with pytest.raises(network.ScanFailure, match="authenticated SOCKS"):
        network.browser_proxy_options()


@pytest.mark.parametrize(
    "message,code",
    [
        ("net::ERR_CERT_AUTHORITY_INVALID", "certificate_error"),
        ("net::ERR_TUNNEL_CONNECTION_FAILED", "proxy_connection"),
        ("net::ERR_NAME_NOT_RESOLVED", "browser_dns"),
        ("net::ERR_EMPTY_RESPONSE", "browser_connection"),
        ("Timeout 10000ms exceeded", "navigation_timeout"),
        ("Executable does not exist. playwright install", "browser_missing"),
    ],
)
def test_connection_errors_identify_actual_failure(message, code):
    assert network.connection_failure(RuntimeError(message)).code == code


@pytest.mark.parametrize(
    "message,retry",
    [
        ("net::ERR_EMPTY_RESPONSE", True),
        ("net::ERR_CONNECTION_RESET", True),
        ("net::ERR_CERT_AUTHORITY_INVALID", False),
        ("HTTP 403", False),
        ("Verify you are human", False),
    ],
)
def test_retry_only_handles_transient_connection_failures(message, retry):
    assert network.can_retry_navigation(RuntimeError(message)) is retry
