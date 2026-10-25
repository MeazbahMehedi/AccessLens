"""Shared browser networking configuration and actionable scan failures."""

import os
import re
from urllib.parse import unquote, urlsplit
from app.core.config import settings


class ScanFailure(RuntimeError):
    def __init__(self, message, code="scan_failed", stage="scan"):
        super().__init__(message)
        self.code = code
        self.stage = stage


def explicit_proxy_url():
    value = settings.browser_proxy_url
    return value.get_secret_value().strip() if value else None


def httpx_proxy_options():
    """Use an explicitly configured proxy for HTTPS DNS and public GitHub too."""
    value = explicit_proxy_url()
    return {"proxy": value} if value else {}


def browser_proxy_options():
    value = explicit_proxy_url()
    source = "explicit" if value else "system"
    if not value and settings.browser_proxy_mode == "auto":
        value = next(
            (
                os.environ.get(k)
                for k in (
                    "HTTPS_PROXY",
                    "https_proxy",
                    "HTTP_PROXY",
                    "http_proxy",
                    "ALL_PROXY",
                    "all_proxy",
                )
                if os.environ.get(k)
            ),
            None,
        )
        if value:
            source = "environment"
    if not value:
        return None, source
    try:
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        if scheme == "socks5h":
            scheme = "socks5"  # Chromium's SOCKS5 proxy resolves remote names.
        if scheme not in {"http", "https", "socks5"} or not parsed.hostname:
            raise ValueError()
        port = parsed.port
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError()
        host = parsed.hostname
        if ":" in host:
            host = f"[{host}]"
        options = {"server": f"{scheme}://{host}" + (f":{port}" if port else "")}
        if parsed.username is not None:
            if scheme == "socks5":
                raise ScanFailure(
                    "Chromium cannot use an authenticated SOCKS proxy. Configure the VPN's HTTP proxy endpoint in BROWSER_PROXY_URL.",
                    "proxy_configuration",
                    "configuration",
                )
            options.update(
                username=unquote(parsed.username), password=unquote(parsed.password or "")
            )
        return options, source
    except ValueError as exc:
        raise ScanFailure(
            "The proxy URL is invalid. Use http://host:port, https://host:port or socks5://host:port in BROWSER_PROXY_URL (or correct the proxy environment variables).",
            "proxy_configuration",
            "configuration",
        ) from exc


def connection_failure(exc):
    """Messages never include proxy credentials or raw network configuration."""
    if isinstance(exc, ScanFailure):
        return exc
    text = str(exc)
    if "ERR_CERT" in text or "SSL" in text:
        return ScanFailure(
            "The website's HTTPS certificate could not be verified. Check the website certificate and your VPN/system trust configuration. AccessLens does not disable certificate checks.",
            "certificate_error",
            "connection",
        )
    if any(code in text for code in ("ERR_PROXY", "ERR_TUNNEL", "ERR_SOCKS")):
        return ScanFailure(
            "Chromium could not connect through the proxy. Keep the VPN connected and check its HTTP/SOCKS endpoint. Set BROWSER_PROXY_URL when a local proxy is required.",
            "proxy_connection",
            "connection",
        )
    if "ERR_NAME_NOT_RESOLVED" in text:
        return ScanFailure(
            "Public DNS verification passed, but Chromium could not resolve the website through its network route. Check the VPN/proxy connection; configure BROWSER_PROXY_URL if your VPN exposes a local proxy.",
            "browser_dns",
            "connection",
        )
    if "Timeout" in type(exc).__name__ or "Timeout" in text or "ERR_TIMED_OUT" in text:
        return ScanFailure(
            "The website did not finish loading within the scan timeout. Try a reachable page or increase SCAN_TIMEOUT_SECONDS.",
            "navigation_timeout",
            "connection",
        )
    if "executable" in text.lower() or "playwright install" in text.lower():
        return ScanFailure(
            "Chromium is not installed for this Python environment. Run: python -m playwright install chromium",
            "browser_missing",
            "browser",
        )
    match = re.search(r"net::(ERR_[A-Z_]+)", text)
    if match:
        return ScanFailure(
            f"The browser could not load the page ({match[1]}). Check website availability and the VPN/proxy connection. This is a connection failure, not an accessibility result.",
            "browser_connection",
            "connection",
        )
    return ScanFailure(
        "The browser could not complete the page inspection. Check the server log for technical details.",
        "browser_error",
        "scan",
    )


def can_retry_navigation(exc):
    # One ordinary recovery attempt only. Never retry HTTP rejection, challenges or TLS failures.
    return any(
        code in str(exc)
        for code in (
            "ERR_CONNECTION_RESET",
            "ERR_CONNECTION_CLOSED",
            "ERR_EMPTY_RESPONSE",
            "ERR_NETWORK_CHANGED",
        )
    )
