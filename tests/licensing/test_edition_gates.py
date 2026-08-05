"""Community vs Enterprise edition gate tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.auth.dependencies import get_current_user
from keprix.licensing.edition import current_edition

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "playbooks" / "canvas"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_default_community(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("KEPRIX_EDITION", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert current_edition() == "community"


@pytest.mark.asyncio
async def test_studio_allowed_community(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KEPRIX_EDITION", "community")
    monkeypatch.setenv("HOME", str(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put("/api/playbooks/studio/daily_digest", json={"canvas": _fixture("linear_three_node.json")})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_fleet_blocked_community(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KEPRIX_EDITION", "community")
    monkeypatch.setenv("HOME", str(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/fleet/instances")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_enterprise_unlocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KEPRIX_EDITION", "enterprise")
    monkeypatch.setenv("HOME", str(tmp_path))
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "role": "admin"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/fleet/instances")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {"instances": []}


@pytest.mark.asyncio
async def test_edition_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_EDITION", "enterprise")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/licensing/edition")

    assert response.status_code == 200
    body = response.json()
    assert body["edition"] == "enterprise"
    assert body["features"]["visual_studio"] is True
    assert body["features"]["fleet_deploy"] is True


@pytest.mark.asyncio
async def test_org_publish_403_in_community(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KEPRIX_EDITION", "community")
    monkeypatch.setenv("HOME", str(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/playbooks/studio/daily_digest", json={"canvas": _fixture("linear_three_node.json")})
        response = await client.post("/api/playbooks/studio/daily_digest/publish", json={"scope": "org"})

    assert response.status_code == 403
