"""Tests for intent HTTP API."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.intent.skill_loader import get_skill_loader


@pytest.mark.asyncio
async def test_intent_schemas_domain_endpoint(intent_env, monkeypatch) -> None:
    get_skill_loader().set_loaded_domains("default", ["borehole_drilling"])
    monkeypatch.setenv("AUTH_ENABLED", "false")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/intent/schemas/borehole_drilling",
            params={"workspace_id": "default"},
        )
    assert response.status_code == 200
    names = {row["name"] for row in response.json()}
    assert "request_drilling_quote" in names


@pytest.mark.asyncio
async def test_intent_extract_endpoint(intent_env, monkeypatch) -> None:
    get_skill_loader().set_loaded_domains("default", ["borehole_drilling"])
    monkeypatch.setenv("AUTH_ENABLED", "false")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/intent/extract",
            json={
                "translated_text": "I want a borehole quote near Tamale",
                "original_text": "Me pe borehole quote wɔ Tamale",
                "source_language": "ak-GH",
                "workspace_id": "default",
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "request_drilling_quote"
