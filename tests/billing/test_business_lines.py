from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.billing import business_lines as lines
from keprix.billing.parity_routes import router


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    monkeypatch.setenv("KEPRIX_BUSINESS_LINE_TIER", "team")
    monkeypatch.setattr(lines, "business_lines_included_below_business", lambda: 1)
    monkeypatch.setattr(lines, "business_lines_unlimited_min_tier", lambda: "business")
    app = FastAPI()
    app.include_router(router)

    async def fake_user() -> dict[str, str]:
        return {"id": "user-1", "username": "user-1"}

    from keprix.auth import dependencies as deps

    app.dependency_overrides[deps.get_current_user] = fake_user
    return TestClient(app)


def test_team_limit_and_delete_frees_slot(client: TestClient) -> None:
    first = client.post("/api/billing/parity/business-lines", json={"workspace_id": "ws1", "name": "Plumbing"})
    assert first.status_code == 201
    second = client.post("/api/billing/parity/business-lines", json={"workspace_id": "ws1", "name": "Roofing"})
    assert second.status_code == 402
    assert second.json()["detail"]["required_tier"] == "business"
    assert second.json()["detail"]["current_tier"] == "team"
    line_id = first.json()["business_line"]["id"]
    assert client.delete(f"/api/billing/parity/business-lines/{line_id}", params={"workspace_id": "ws1"}).status_code == 200
    assert client.post("/api/billing/parity/business-lines", json={"workspace_id": "ws1", "name": "Roofing"}).status_code == 201


def test_business_tier_is_unlimited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_BUSINESS_LINE_TIER", "business")
    for name in ("One", "Two", "Three"):
        assert client.post("/api/billing/parity/business-lines", json={"workspace_id": "ws2", "name": name}).status_code == 201
    status = client.get("/api/billing/parity/business-lines/status", params={"workspace_id": "ws2"}).json()
    assert status["unlimited"] is True
    assert status["can_add"] is True
