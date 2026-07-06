"""Tests for localization HTTP API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_languages_api_akan_with_sm4t_enabled() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/localization/languages", params={"sm4t_enabled": True})
    assert response.status_code == 200
    languages = {item["code"]: item for item in response.json()["languages"]}
    assert "ak-GH" in languages
    akan = languages["ak-GH"]
    assert akan["transcription"] is True
    assert akan["translation"] is True
    assert akan["speech"] is True
    assert "seamless_m4t" in akan["providers"]


@pytest.mark.asyncio
async def test_provider_health_reports_error_when_sidecars_unreachable() -> None:
    mock_client = AsyncMock()
    mock_client.get.side_effect = ConnectionError("sidecar unavailable")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("keprix.backend.localization.providers.seamless_m4t.httpx.AsyncClient", return_value=mock_client), patch(
        "keprix.backend.localization.providers.nllb_200.httpx.AsyncClient",
        return_value=mock_client,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/localization/providers/health")
    assert response.status_code == 200
    body = response.json()
    assert body["seamless_m4t"]["status"] == "error"
    assert body["nllb_200"]["status"] == "error"

