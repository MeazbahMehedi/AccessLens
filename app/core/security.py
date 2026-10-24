"""Public-target validation, including VPN/proxy synthetic-DNS compatibility.

A synthetic DNS answer is never sufficient authorization: verify the hostname
independently over HTTPS and require every returned IPv4/IPv6 address to be public.
Literal private/reserved IP URLs and real private DNS answers remain blocked.
"""

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import ipaddress
import socket
from threading import Lock
import time
from urllib.parse import urlparse
import httpx
from app.core.config import settings
from app.core.network import httpx_proxy_options


class UnsafeURLError(ValueError):
    """Raised when a target is malformed, non-public, or cannot be verified."""


class DNSVerificationError(UnsafeURLError):
    """DNS verification could not complete; this is a connectivity/configuration error."""


# These are fixed HTTPS services, never URLs supplied by website input.
DOH_PROVIDERS = ("https://dns.google/resolve", "https://cloudflare-dns.com/dns-query")
SYNTHETIC_IPV4 = ipaddress.ip_network("198.18.0.0/15")
SYNTHETIC_IPV6 = ipaddress.ip_network("2001:2::/48")
_CACHE_LIMIT = 256
_doh_cache = OrderedDict()
_cache_lock = Lock()


@dataclass(frozen=True)
class DNSAnswer:
    addresses: tuple
    ttl: int = 30
    provider: str = ""


def _address(raw):
    address = ipaddress.ip_address(raw)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def _is_public(address):
    return address.is_global and not address.is_multicast


def _is_synthetic(address):
    return (isinstance(address, ipaddress.IPv4Address) and address in SYNTHETIC_IPV4) or (
        isinstance(address, ipaddress.IPv6Address) and address in SYNTHETIC_IPV6
    )


def _require_public(hostname, addresses):
    if not addresses:
        raise UnsafeURLError(f"No public IPv4 or IPv6 records were found for {hostname}.")
    for address in addresses:
        if not _is_public(address):
            raise UnsafeURLError(
                f"{hostname} resolves to a non-public address ({address}). "
                "Local, private and reserved destinations cannot be scanned."
            )


def _resolve_system(hostname):
    """Resolve with the OS; a VPN may substitute synthetic IPv4 or IPv6 addresses."""
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise DNSVerificationError(f"System DNS could not resolve {hostname}.") from exc
    return list(dict.fromkeys(_address(i[4][0].split("%")[0]) for i in infos))


def _query_dns(client, provider, hostname, record_type):
    response = client.get(provider, params={"name": hostname, "type": record_type})
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or type(result.get("Status")) is not int:
        raise ValueError("Invalid DNS response")
    if result["Status"] == 3:
        raise UnsafeURLError(f"Public DNS could not find {hostname}. Check the website address.")
    if result["Status"] != 0 or result.get("TC"):
        raise ValueError("DNS resolver did not return a complete successful answer")
    answers = result.get("Answer", [])
    if not isinstance(answers, list):
        raise ValueError("Invalid DNS answer list")
    addresses, ttls = [], []
    for item in answers:
        if not isinstance(item, dict):
            raise ValueError("Invalid DNS record")
        if item.get("type") not in (1, 28):
            continue  # CNAME chains are resolved by the recursive HTTPS service.
        address = ipaddress.ip_address(item.get("data", ""))
        if (item["type"] == 1 and address.version != 4) or (
            item["type"] == 28 and address.version != 6
        ):
            raise ValueError("Address family does not match DNS record")
        addresses.append(_address(str(address)))
        ttl = item.get("TTL", 0)
        ttls.append(ttl if type(ttl) is int and ttl >= 0 else 0)
    return addresses, ttls


def _resolve_public_dns(hostname):
    """Check both A and AAAA over verified HTTPS; cache only public successes."""
    with _cache_lock:
        cached = _doh_cache.get(hostname)
        if cached and cached[0] > time.monotonic():
            _doh_cache.move_to_end(hostname)
            return cached[1]
        _doh_cache.pop(hostname, None)
    for provider in DOH_PROVIDERS:
        try:
            with (
                httpx.Client(
                    timeout=settings.dns_https_timeout_seconds,
                    **httpx_proxy_options(),
                    follow_redirects=False,
                    headers={"Accept": "application/dns-json", "User-Agent": "AccessCheck/2.0.2"},
                ) as client,
                ThreadPoolExecutor(max_workers=2) as pool,
            ):
                # Verify both families: a public A record must not hide a private AAAA.
                futures = [
                    pool.submit(_query_dns, client, provider, hostname, kind)
                    for kind in ("A", "AAAA")
                ]
                results, errors = [], []
                for future in futures:
                    try:
                        results.append(future.result())
                    except (httpx.HTTPError, ValueError, ImportError, OSError) as exc:
                        errors.append(exc)
            addresses = tuple(dict.fromkeys(ip for ips, _ in results for ip in ips))
            for error in errors:
                if isinstance(error, UnsafeURLError):
                    raise error
            if addresses:
                _require_public(hostname, addresses)
            if errors:
                raise errors[0]
            _require_public(hostname, addresses)  # Never override a genuine private answer.
            ttls = [ttl for _, values in results for ttl in values]
            ttl = min(60, min(ttls)) if ttls else 0
            answer = DNSAnswer(addresses, ttl, provider)
            if ttl:
                with _cache_lock:
                    _doh_cache[hostname] = (time.monotonic() + ttl, answer)
                    _doh_cache.move_to_end(hostname)
                    while len(_doh_cache) > _CACHE_LIMIT:
                        _doh_cache.popitem(last=False)
            return answer
        except UnsafeURLError:
            raise
        except (httpx.HTTPError, ValueError, ImportError, OSError):
            continue
    raise DNSVerificationError(
        f"HTTPS DNS verification is unavailable for {hostname}. "
        "Check your internet/VPN/proxy connection and access to Google or Cloudflare DNS, then retry. "
        "The hostname was not treated as a private website; its real public address could not be verified."
    )


def _resolve_hostname(hostname):
    try:
        addresses = _resolve_system(hostname)
    except DNSVerificationError as exc:
        if not settings.dns_public_fallback:
            raise DNSVerificationError(
                f"System DNS could not resolve {hostname}. Enable DNS_PUBLIC_FALLBACK or fix your DNS configuration."
            ) from exc
        return _resolve_public_dns(hostname).addresses
    if not addresses:
        if settings.dns_public_fallback:
            return _resolve_public_dns(hostname).addresses
        raise DNSVerificationError(f"System DNS returned no addresses for {hostname}.")
    has_synthetic = any(_is_synthetic(ip) for ip in addresses)
    # An actual private/loopback/link-local answer is always rejected, even when
    # another answer is synthetic or public. Do not mask hosts-file/LAN mappings.
    real_answers = [ip for ip in addresses if not _is_synthetic(ip)]
    if real_answers:
        _require_public(hostname, real_answers)
    if has_synthetic:
        if not settings.dns_public_fallback:
            raise DNSVerificationError(
                f"Your DNS returned a VPN/proxy synthetic address for {hostname}. "
                "Enable DNS_PUBLIC_FALLBACK or configure the proxy to return real DNS answers."
            )
        try:
            return _resolve_public_dns(hostname).addresses
        except DNSVerificationError as exc:
            raise DNSVerificationError(
                f"Your VPN/proxy DNS returned a synthetic address for {hostname}, "
                f"not proof of a private website. {exc}"
            ) from exc
    return addresses


def normalize_url(raw):
    """Accept example.com by adding https:// when no scheme was typed."""
    raw = (raw or "").strip()
    if raw and "://" not in raw:
        raw = "https://" + raw
    return raw


def validate_public_url(url):
    """Return the original URL after validating its real public hostname records."""
    url = url.strip()
    if any(ord(ch) < 32 or ch.isspace() for ch in url):
        raise UnsafeURLError("The URL contains spaces or control characters. Encode spaces as %20.")
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise UnsafeURLError("Invalid website URL.") from exc
    if parsed.scheme.lower() not in ("http", "https") or not hostname:
        raise UnsafeURLError("Enter a complete website URL starting with https:// or http://.")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs containing credentials are not allowed.")
    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(
        (".localhost", ".local", ".internal", ".lan", ".home.arpa")
    ):
        raise UnsafeURLError("Local website addresses are blocked.")
    try:
        literal = _address(hostname)
    except ValueError:
        try:
            hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise UnsafeURLError("Invalid website hostname.") from exc
        addresses = _resolve_hostname(hostname)
    else:
        # A literal reserved IPv4/IPv6 address is never accepted as a proxy hostname.
        addresses = [literal]
    _require_public(hostname, addresses)
    return url
