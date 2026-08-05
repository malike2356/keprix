"""Scout Warden client degradation tests."""

from __future__ import annotations

import httpx
import pytest

from keprix.integrations.scout_warden import ScoutWardenClient


@pytest.mark.asyncio
async def test_disabled_by_default() -> None:
    result = await ScoutWardenClient(base_url="http://scout.test").request_scan(target="https://example.com")
    assert result.get("disabled") is True


@pytest.mark.asyncio
async def test_mocked_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_SCOUT_WARDEN_ENABLED", "1")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/scans"
        return httpx.Response(200, json={"id": "scan-1", "status": "queued"})

    transport = httpx.MockTransport(handler)
    client = ScoutWardenClient(base_url="http://scout.test", transport=transport)
    result = await client.request_scan(target="https://example.com", tenant_id="local")
    assert result["ok"] is True
    assert result["scan"]["id"] == "scan-1"
