"""Published knowledge, customer cases, handoff (Prompt 631)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.auth import dependencies as deps
from keprix.customer_concierge.audience.store import reset_audience_store_for_tests
from keprix.customer_concierge.published_knowledge import reset_knowledge_store_for_tests
from keprix.customer_concierge.routes import public_router, router
from keprix.customer_concierge.store import reset_concierge_store_for_tests
from keprix.customer_concierge.support_cases import (
    PRODUCT_SUPPORT_SCOPE,
    SCOPE,
    reset_support_case_store_for_tests,
)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "k631.sqlite"


@pytest.fixture()
def client(db_path: Path, monkeypatch):
    monkeypatch.setenv("KEPRIX_CONCIERGE_DB_PATH", str(db_path))
    reset_concierge_store_for_tests(db_path)
    reset_audience_store_for_tests(db_path)
    reset_knowledge_store_for_tests(db_path)
    reset_support_case_store_for_tests(db_path)
    app = FastAPI()
    app.include_router(router)
    app.include_router(public_router)
    app.dependency_overrides[deps.get_current_user] = lambda: {"id": "op1", "username": "op1"}
    with TestClient(app) as tc:
        yield tc


def _publish(client: TestClient) -> None:
    assert (
        client.post(
            "/api/customer-concierge/setup/step1",
            json={
                "personaId": "default",
                "personaName": "Desk",
                "greetingMessage": "Hi there",
                "businessName": "Acme",
                "businessDescription": "Demos",
                "escalationEmail": "ops@acme.test",
                "knowledgeSourceIds": [],
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/customer-concierge/setup/step2",
            json={
                "personaId": "default",
                "channels": {
                    "web": {"enabled": True},
                    "policy": {
                        "confidenceThreshold": 0.45,
                        "sensitiveIntents": ["vip cancel"],
                        "slaFirstResponseMinutes": 30,
                    },
                },
                "businessHours": {"timezone": "UTC", "windows": []},
                "calendarProvider": None,
                "conferencingProvider": None,
                "meetingTypes": [],
                "icsFallbackOk": True,
            },
        ).status_code
        == 200
    )
    assert client.post("/api/customer-concierge/publish?personaId=default").status_code == 200


def _open_session(client: TestClient) -> dict:
    r = client.post("/api/customer-concierge/public/op1/default/session", json={})
    assert r.status_code == 200, r.text
    return r.json()


def test_only_published_sources_in_external_answers(client: TestClient) -> None:
    _publish(client)
    created = client.post(
        "/api/customer-concierge/knowledge",
        json={
            "personaId": "default",
            "title": "Pricing FAQ",
            "content": "Our starter plan costs fifty pounds per month for small teams.",
            "type": "faq",
        },
    )
    assert created.status_code == 200
    source_id = created.json()["source"]["id"]
    assert created.json()["source"]["publishState"] == "draft"

    session = _open_session(client)
    sid = session["sessionId"]
    token = session["widgetSessionToken"]

    # Draft must not ground visitor answers
    draft_msg = client.post(
        f"/api/customer-concierge/public/op1/default/session/{sid}/message",
        json={"text": "How much is the starter plan?", "widgetSessionToken": token},
    )
    assert draft_msg.status_code == 200
    assert draft_msg.json()["grounded"] is False
    assert "fifty pounds" not in draft_msg.json()["reply"].lower()

    pub = client.post(
        f"/api/customer-concierge/knowledge/{source_id}/publish-state",
        json={"publishState": "published"},
    )
    assert pub.status_code == 200
    assert pub.json()["source"]["publishState"] == "published"

    session2 = _open_session(client)
    ok = client.post(
        f"/api/customer-concierge/public/op1/default/session/{session2['sessionId']}/message",
        json={
            "text": "How much is the starter plan?",
            "widgetSessionToken": session2["widgetSessionToken"],
        },
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["grounded"] is True
    assert "fifty pounds" in body["reply"].lower()
    assert body["citations"]
    assert body["internalNotesVisible"] is False


def test_sensitive_intent_and_low_confidence_escalate(client: TestClient) -> None:
    _publish(client)
    created = client.post(
        "/api/customer-concierge/knowledge",
        json={
            "personaId": "default",
            "title": "Office hours",
            "content": "We are open Monday to Friday nine to five London time.",
            "type": "faq",
        },
    )
    source_id = created.json()["source"]["id"]
    client.post(
        f"/api/customer-concierge/knowledge/{source_id}/publish-state",
        json={"publishState": "published"},
    )

    session = _open_session(client)
    sensitive = client.post(
        f"/api/customer-concierge/public/op1/default/session/{session['sessionId']}/message",
        json={
            "text": "I need a refund and may file a lawsuit",
            "widgetSessionToken": session["widgetSessionToken"],
        },
    )
    assert sensitive.status_code == 200
    assert sensitive.json()["escalated"] is True
    assert str(sensitive.json().get("fallbackReason", "")).startswith("sensitive_intent")
    assert sensitive.json().get("supportCase")
    assert sensitive.json()["supportCase"]["scope"] == SCOPE

    session2 = _open_session(client)
    low = client.post(
        f"/api/customer-concierge/public/op1/default/session/{session2['sessionId']}/message",
        json={
            "text": "xyzzy unrelated quantum banana",
            "widgetSessionToken": session2["widgetSessionToken"],
        },
    )
    assert low.status_code == 200
    assert low.json()["escalated"] is True
    assert low.json().get("fallbackReason") in {"no_published_match", "low_confidence"}


def test_internal_notes_owner_only(client: TestClient) -> None:
    _publish(client)
    session = _open_session(client)
    # Create case via tool
    case_msg = client.post(
        f"/api/customer-concierge/public/op1/default/session/{session['sessionId']}/message",
        json={
            "text": "Need help",
            "tool": "support-case-create",
            "toolArgs": {"subject": "Help please"},
            "widgetSessionToken": session["widgetSessionToken"],
        },
    )
    assert case_msg.status_code == 200, case_msg.text
    case_id = case_msg.json()["supportCase"]["id"]

    note = client.post(
        f"/api/customer-concierge/cases/{case_id}/notes",
        json={"body": "VIP customer, do not discount"},
    )
    assert note.status_code == 200
    assert note.json()["visibility"] == "owner_only"

    # Public message must never include the note text
    pub = client.post(
        f"/api/customer-concierge/public/op1/default/session/{session['sessionId']}/message",
        json={"text": "any update?", "widgetSessionToken": session["widgetSessionToken"]},
    )
    assert pub.status_code == 200
    assert "VIP customer" not in pub.json()["reply"]
    assert "do not discount" not in pub.json().get("reply", "")
    assert pub.json().get("internalNotesVisible") is False

    op_view = client.get(f"/api/customer-concierge/cases/{case_id}")
    assert op_view.status_code == 200
    assert any("VIP customer" in n["body"] for n in op_view.json()["internalNotes"])


def test_customer_cases_not_product_support(client: TestClient) -> None:
    _publish(client)
    cases = client.get("/api/customer-concierge/cases?personaId=default")
    assert cases.status_code == 200
    body = cases.json()
    assert body["scope"] == SCOPE
    assert body["productSupportScope"] == PRODUCT_SUPPORT_SCOPE
    assert "/api/support" in body["note"]

    session = _open_session(client)
    handoff = client.post(
        f"/api/customer-concierge/public/op1/default/session/{session['sessionId']}/message",
        json={
            "tool": "handoff-request",
            "toolArgs": {"reason": "Want a human"},
            "widgetSessionToken": session["widgetSessionToken"],
            "text": "human please",
        },
    )
    assert handoff.status_code == 200
    assert handoff.json()["status"] == "handed_off"
    assert handoff.json()["supportCase"]["scope"] == SCOPE
    assert handoff.json()["channelContinuous"] is True

    takeover = client.post(f"/api/customer-concierge/sessions/{session['sessionId']}/takeover")
    assert takeover.status_code == 200
    assert takeover.json()["liveTakeover"] is True
    assert takeover.json()["operatorUserId"] == "op1"

    release = client.post(f"/api/customer-concierge/sessions/{session['sessionId']}/release")
    assert release.status_code == 200
    assert release.json()["status"] == "active"
