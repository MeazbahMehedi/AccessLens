"""Read-only public GitHub data for the fixed developer account."""

import asyncio
import time
from datetime import datetime, timezone
import httpx
from app.core.network import httpx_proxy_options

USERNAME = "ItsMONIKAAKTER"
_cache = None
_cached_at = 0
_retry_at = 0
_lock = asyncio.Lock()


async def developer_data():
    global _cache, _cached_at, _retry_at
    now = time.monotonic()
    if _cache and now - _cached_at < 600:
        return {**_cache, "stale": False, "error": None}
    if now < _retry_at:
        return {
            **(_cache or {"profile": None, "repos": [], "username": USERNAME}),
            "stale": bool(_cache),
            "error": "GitHub is temporarily unavailable or rate limited. Try again shortly.",
        }
    async with _lock:
        if _cache and time.monotonic() - _cached_at < 600:
            return {**_cache, "stale": False, "error": None}
        try:
            async with (
                asyncio.timeout(40),
                httpx.AsyncClient(
                    **httpx_proxy_options(),
                    base_url="https://api.github.com",
                    timeout=10,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "AccessCheck/2.0",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                ) as client,
            ):
                response = await client.get(f"/users/{USERNAME}")
                response.raise_for_status()
                profile = response.json()
                repos = []
                truncated = False
                for page in range(1, 21):
                    response = await client.get(
                        f"/users/{USERNAME}/repos",
                        params={
                            "per_page": 100,
                            "page": page,
                            "sort": "updated",
                            "direction": "desc",
                            "type": "owner",
                        },
                    )
                    response.raise_for_status()
                    batch = response.json()
                    repos.extend(batch)
                    if len(batch) < 100:
                        break
                else:
                    truncated = True
                _cache = {
                    "username": USERNAME,
                    "profile": profile,
                    "repos": repos,
                    "truncated": truncated,
                    "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                }
                _cached_at = time.monotonic()
                return {**_cache, "stale": False, "error": None}
        except (httpx.HTTPError, TimeoutError, ValueError, ImportError):
            _retry_at = time.monotonic() + 60
            return {
                **(_cache or {"username": USERNAME, "profile": None, "repos": []}),
                "stale": bool(_cache),
                "error": "GitHub is temporarily unavailable or rate limited. Public data could not be refreshed.",
            }
