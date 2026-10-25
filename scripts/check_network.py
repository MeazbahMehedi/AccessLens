"""Explain DNS validation for one URL without submitting a scan or changing settings."""

import argparse
import asyncio
from pathlib import Path
import sys
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core import security


def main():
    parser = argparse.ArgumentParser(
        description="Check AccessLens public-URL and VPN/proxy DNS verification."
    )
    parser.add_argument("url", help="A website URL or hostname, for example jwxt.zzu.edu.cn")
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Also load the page in Chromium and run the real accessibility engine (no database write).",
    )
    args = parser.parse_args()
    url = security.normalize_url(args.url)
    try:
        host = urlparse(url).hostname
        if not host:
            raise ValueError("A website hostname is required.")
        print(f"Website: {host}")
        try:
            addresses = security._resolve_system(host)
            print("System DNS: " + ", ".join(str(ip) for ip in addresses))
            if any(security._is_synthetic(ip) for ip in addresses):
                print(
                    "Detected: VPN/proxy-style synthetic DNS. Independent public verification is required."
                )
        except security.DNSVerificationError:
            print("System DNS: unavailable. HTTPS DNS fallback will be used when enabled.")
        security.validate_public_url(url)
        print("Public-target validation: PASSED")
        if args.browser:
            from app.core.network import browser_proxy_options
            from app.engine.scanner import scan_page_isolated
            from app.services.scoring import calculate_score
            from app.engine.scanner import finding_dict

            print(f"Browser route: {browser_proxy_options()[1]}")
            try:
                result = asyncio.run(scan_page_isolated(url))
            except Exception as exc:
                print(f"Browser scan: FAILED\n{exc}")
                return 2
            print(
                f"Browser scan: PASSED\nTitle: {result.title}\nEngine: {result.metadata.get('engine')}\nFindings: {len(result.findings)}\nHeuristic score: {calculate_score([finding_dict(i) for i in result.findings])}/100"
            )
            for note in result.notes:
                print(f"Note: {note}")
        else:
            print(
                "The URL is eligible for scanning. Use --browser to test the complete browser/engine path."
            )
        return 0
    except (security.UnsafeURLError, ValueError) as exc:
        print(f"Public-target validation: FAILED\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
