"""API smoke for /api/vical routes (TestClient)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.vical.routes import router as vical_router
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import vical_store
from keprix.workspace.repository import workspace_repo


@pytest.fixture(autouse=True)
def clean() -> None:
    workspace_repo.calendar_events.clear()
    vical_store.clear()
    yield
    workspace_repo.calendar_events.clear()
    vical_store.clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(vical_router)

    async def fake_user():
        return {"id": "api-user", "username": "api-user"}

    from keprix.auth import dependencies as deps

    app.dependency_overrides[deps.get_current_user] = fake_user
    return TestClient(app)


def test_status_and_slots(client: TestClient) -> None:
    res = client.get("/api/vical/status")
    assert res.status_code == 200
    assert res.json()["enabled"] is True
    start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    slots = client.get("/api/vical/slots", params={"slug": "consultation", "count": 3})
    assert slots.status_code == 200
    assert isinstance(slots.json()["items"], list)


def test_create_booking_via_api(client: TestClient) -> None:
    ensure_default_consultation("api-user")
    start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=2)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    body = {
        "guest_name": "Api Guest",
        "guest_email": "guest@example.com",
        "starts_at": start.isoformat(),
        "slug": "consultation",
        "source": "api",
    }
    res = client.post("/api/vical/bookings", json=body)
    assert res.status_code == 201, res.text
    payload = res.json()
    assert payload["status"] == "confirmed"
    assert payload["workspace_event_id"]


def test_create_booking_skip_slot_check(client: TestClient) -> None:
    """Host calendar free-slot create may land outside offer windows."""
    ensure_default_consultation("api-user")
    start = datetime.now(timezone.utc).replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(days=3)
    body = {
        "guest_name": "Slot Guest",
        "guest_email": "slot@example.com",
        "starts_at": start.isoformat(),
        "slug": "consultation",
        "source": "api",
        "skip_slot_check": True,
    }
    res = client.post("/api/vical/bookings", json=body)
    assert res.status_code == 201, res.text
    assert res.json()["guest_email"] == "slot@example.com"
