import asyncio
import httpx
import pytest
from app.services import github_service as service


@pytest.mark.asyncio
async def test_profile_pagination_cache_and_outage(monkeypatch):
    service._cache = None
    service._cached_at = 0
    service._retry_at = 0
    service._lock = asyncio.Lock()
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path.endswith("/repos"):
            page = request.url.params["page"]
            return httpx.Response(
                200,
                json=[{"name": f"repo{i}"} for i in range(100)]
                if page == "1"
                else [{"name": "last-repo"}],
            )
        return httpx.Response(200, json={"login": "MeazbahMehedi", "public_repos": 101})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        service.httpx,
        "AsyncClient",
        lambda **kw: real(**kw, transport=httpx.MockTransport(handler), trust_env=False),
    )
    data = await service.developer_data()
    assert data["profile"]["login"] == "MeazbahMehedi"
    assert len(data["repos"]) == 101
    await service.developer_data()
    assert len(calls) == 3
    service._cached_at = 0

    def fail(request):
        return httpx.Response(403, json={"message": "rate limited"})

    monkeypatch.setattr(
        service.httpx,
        "AsyncClient",
        lambda **kw: real(**kw, transport=httpx.MockTransport(fail), trust_env=False),
    )
    stale = await service.developer_data()
    assert stale["stale"]
    assert len(stale["repos"]) == 101
    assert stale["error"]


@pytest.mark.asyncio
async def test_profile_unavailable_has_no_fake_data(monkeypatch):
    service._cache = None
    service._cached_at = 0
    service._retry_at = 0
    service._lock = asyncio.Lock()
    real = httpx.AsyncClient
    monkeypatch.setattr(
        service.httpx,
        "AsyncClient",
        lambda **kw: real(
            **kw, transport=httpx.MockTransport(lambda r: httpx.Response(404)), trust_env=False
        ),
    )
    data = await service.developer_data()
    assert data["profile"] is None
    assert data["repos"] == []
    assert data["error"]
