import socket
import ssl
import certifi
import ipaddress
import json
import urllib.parse
import urllib.request
from urllib.error import URLError
from urllib.parse import urlparse


class UnsafeURLError(ValueError):
    """Raised when a target URL is not safe to scan."""


DOH_ENDPOINT = "https://cloudflare-dns.com/dns-query"


def _resolve_public_addresses(hostname: str) -> list:
    """Resolve a hostname using DNS-over-HTTPS."""
    addresses = []

    for record_type in ("A", "AAAA"):
        query = urllib.parse.urlencode({
            "name": hostname,
            "type": record_type,
        })
        request = urllib.request.Request(
            f"{DOH_ENDPOINT}?{query}",
            headers={
                "Accept": "application/dns-json",
                "User-Agent": "AccessCheck/1.0",
            },
        )

        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())

            with urllib.request.urlopen(
                    request,
                    timeout=8,
                    context=ssl_context,
            ) as response:

                result = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, ValueError):
            # DoH blocked (firewall/school/VPN)? Fall back to the OS resolver.
            return _resolve_system(hostname)

        if result.get("Status") not in (0, 3):
            raise UnsafeURLError(
                f"DNS verification failed for {hostname}."
            )

        for answer in result.get("Answer", []):
            if answer.get("type") in (1, 28):
                try:
                    addresses.append(
                        ipaddress.ip_address(answer["data"])
                    )
                except (ValueError, KeyError):
                    continue

    if not addresses:
        raise UnsafeURLError(
            f"No public A or AAAA records were found for {hostname}."
        )

    return addresses


def _resolve_system(hostname: str) -> list:
    """Fallback resolver. Every returned address is still checked as public."""
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve {hostname}. Check the address.") from exc
    return [ipaddress.ip_address(i[4][0].split("%")[0]) for i in infos]


def normalize_url(raw: str) -> str:
    """Accept 'example.com' by adding https:// when no scheme was typed."""
    raw = (raw or "").strip()
    if raw and "://" not in raw:
        raw = "https://" + raw
    return raw


def validate_public_url(url: str) -> str:
    """Validate a URL against non-public destination addresses."""
    url = url.strip()

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        parsed.port  # Force validation of malformed ports.
    except ValueError as exc:
        raise UnsafeURLError("Invalid website URL.") from exc

    scheme = parsed.scheme.lower()

    if scheme not in ("http", "https") or not hostname:
        raise UnsafeURLError(
            "Enter a complete website URL starting with https:// or http://."
        )

    if parsed.username or parsed.password:
        raise UnsafeURLError(
            "URLs containing credentials are not allowed."
        )

    hostname = hostname.rstrip(".").lower()

    if (
        hostname == "localhost"
        or hostname.endswith((".localhost", ".local"))
    ):
        raise UnsafeURLError("Local website addresses are blocked.")

    # Literal IPs must be checked directly; never resolve them as hostnames.
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        addresses = _resolve_public_addresses(hostname)

    for address in addresses:
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped

        if not address.is_global:
            raise UnsafeURLError(
                f"{hostname} has a non-public address ({address}). "
                "AccessCheck blocks non-public destinations."
            )

    return url
