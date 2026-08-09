"""Customer Concierge setup wizard tests (Prompt 628)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.auth import dependencies as deps
from keprix.customer_concierge.prompt_overlay import build_concierge_persona_overlay
from keprix.customer_concierge.readiness import evaluate_readiness
from keprix.customer_concierge.routes import public_router, router
from keprix.customer_concierge.audience.store import reset_audience_store_for_tests
from keprix.customer_concierge.store import reset_concierge_store_for_tests


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "concierge.sqlite"


@pytest.fixture()
def store(db_path: Path):
    reset_audience_store_for_tests(db_path)
    return reset_concierge_store_for_tests(db_path)


@pytest.fixture()
def client(db_path: Path, monkeypatch):
    monkeypatch.setenv("KEPRIX_CONCIERGE_DB_PATH", str(db_path))
    reset_concierge_store_for_tests(db_path)
    reset_audience_store_for_tests(db_path)
    app = FastAPI()
    app.include_router(router)
    app.include_router(public_router)
    app.dependency_overrides[deps.get_current_user] = lambda: {"id": "op1", "username": "op1"}
    with TestClient(app) as tc:
        yield tc


def _step1(client: TestClient, **extra):
    body = {
        "personaId": "default",
        "personaName": "Front Desk",
        "greetingMessage": "Welcome to Acme.",
        "businessName": "Acme Ltd",
        "businessDescription": "We help small businesses book demos.",
        "escalationEmail": "ops@acme.test",
        "knowledgeSourceIds": ["kb-1"],
        **extra,
    }
    return client.post("/api/customer-concierge/setup/step1", json=body)


def _step2_ce(client: TestClient):
    return client.post(
        "/api/customer-concierge/setup/step2",
        json={
            "personaId": "default",
            "channels": {"web": {"enabled": True}},
            "businessHours": {
                "timezone": "Europe/London",
                "windows": [{"dayOfWeek": 1, "start": "09:00", "end": "17:00"}],
            },
            "calendarProvider": None,
            "conferencingProvider": None,
            "meetingTypes": [],
            "icsFallbackOk": True,
        },
    )


def test_wizard_two_steps_persist(client: TestClient, db_path: Path) -> None:
    r1 = _step1(client)
    assert r1.status_code == 200, r1.text
    r2 = _step2_ce(client)
    assert r2.status_code == 200, r2.text
    from keprix.customer_concierge.store import get_concierge_store

    profile = get_concierge_store(db_path).get("op1", "default")
    assert profile is not None
    assert profile.persona_name == "Front Desk"
    assert (profile.channel_config.get("web") or {}).get("enabled") is True


def test_ce_no_provider_readiness_and_publish(client: TestClient) -> None:
    assert _step1(client).status_code == 200
    assert _step2_ce(client).status_code == 200
    ready = client.get("/api/customer-concierge/readiness?personaId=default")
    assert ready.status_code == 200
    body = ready.json()
    assert body["ready"] is True
    assert "calendar" not in body["blockers"]
    assert "conferencing" not in body["blockers"]
    pub = client.post("/api/customer-concierge/publish?personaId=default")
    assert pub.status_code == 200, pub.text
    assert pub.json()["profile"]["published"] is True
    overlay = pub.json().get("personaOverlay") or ""
    assert "Front Desk" in overlay and "Acme Ltd" in overlay
    assert "ops@acme.test" in overlay
    assert "Welcome to Acme" in overlay


def test_publish_blocked_when_meeting_types_need_providers(client: TestClient, db_path: Path) -> None:
    assert _step1(client).status_code == 200
    r2 = client.post(
        "/api/customer-concierge/setup/step2",
        json={
            "personaId": "default",
            "channels": {"web": {"enabled": True}},
            "businessHours": {"timezone": "UTC", "windows": []},
            "calendarProvider": "google",
            "conferencingProvider": "zoom",
            "calendarConnected": False,
            "conferencingConnected": False,
            "meetingTypes": [{"name": "Demo", "durationMinutes": 30}],
            "icsFallbackOk": True,
        },
    )
    assert r2.status_code == 200, r2.text
    from keprix.customer_concierge.store import get_concierge_store

    ready = evaluate_readiness("op1", "default", store=get_concierge_store(db_path))
    assert ready["ready"] is False
    assert "calendar" in ready["blockers"]
    assert "conferencing" in ready["blockers"]
    pub = client.post("/api/customer-concierge/publish?personaId=default")
    assert pub.status_code == 400


def test_unpublish_rejects_new_sessions_keeps_existing(client: TestClient) -> None:
    assert _step1(client).status_code == 200
    assert _step2_ce(client).status_code == 200
    assert client.post("/api/customer-concierge/publish?personaId=default").status_code == 200

    opened = client.post("/api/customer-concierge/public/op1/default/session", json={})
    assert opened.status_code == 200
    session_id = opened.json()["sessionId"]
    assert opened.json()["workspaceMember"] is False

    assert client.post("/api/customer-concierge/unpublish?personaId=default").status_code == 200

    rejected = client.post("/api/customer-concierge/public/op1/default/session", json={})
    assert rejected.status_code == 403

    msg = client.post(
        f"/api/customer-concierge/public/op1/default/session/{session_id}/message",
        json={"text": "still here"},
    )
    assert msg.status_code == 200
    assert msg.json()["ok"] is True


def test_public_widget_greeting_when_published(client: TestClient) -> None:
    assert _step1(client).status_code == 200
    assert _step2_ce(client).status_code == 200
    assert client.post("/api/customer-concierge/publish?personaId=default").status_code == 200
    status = client.get("/api/customer-concierge/public/op1/default/status")
    assert status.status_code == 200
    assert status.json()["published"] is True
    assert status.json()["greeting"] == "Welcome to Acme."


def test_persona_overlay_includes_profile_fields(store) -> None:
    profile = store.upsert_step1(
        workspace_id="ws1",
        persona_id="p1",
        persona_name="Nova",
        greeting_message="Hello",
        business_name="Nova Co",
        business_description="Demos and support",
        escalation_email="help@nova.test",
        knowledge_source_ids=["src-a", "src-b"],
    )
    store.upsert_step2(
        workspace_id="ws1",
        persona_id="p1",
        channels={"web": {"enabled": True}},
        business_hours={
            "timezone": "Europe/London",
            "windows": [{"dayOfWeek": 1, "start": "09:00", "end": "17:00"}],
        },
    )
    overlay = build_concierge_persona_overlay(store.get("ws1", "p1"))  # type: ignore[arg-type]
    assert "Nova" in overlay
    assert "Nova Co" in overlay
    assert "src-a" in overlay and "src-b" in overlay
    assert "help@nova.test" in overlay
    assert "Europe/London" in overlay
    assert profile.greeting_message == "Hello"


def test_package_has_no_carina_runtime() -> None:
    from keprix import customer_concierge

    assert customer_concierge.CARINA_RUNTIME_REQUIRED is False
