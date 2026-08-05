"""API tests for clarify/approval respond endpoints (Prompt 202)."""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.api.web_ui_prompt_bridge import respond_approval, respond_clarify
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from tools import approval as approval_mod
from tools import clarify_gateway as clarify_mod


@pytest.fixture
def prompt_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_respond_clarify_unblocks_agent_thread() -> None:
    session_id = "sess-clarify"
    clarify_mod.register(
        clarify_id="cid123",
        session_key=session_id,
        question="Pick",
        choices=["A", "B"],
    )
    resolved: list[str] = []

    def _waiter() -> None:
        answer = clarify_mod.wait_for_response("cid123", timeout=5.0)
        resolved.append(str(answer))

    thread = threading.Thread(target=_waiter, daemon=True)
    thread.start()
    assert respond_clarify("cid123", "A") is True
    thread.join(timeout=2.0)
    assert resolved == ["A"]
    clarify_mod.clear_session(session_id)


def test_respond_clarify_missing_returns_false() -> None:
    assert respond_clarify("missing-id", "hello") is False


def test_respond_approval_resolves_gateway_queue() -> None:
    session_id = "sess-approval"
    approval_data = {
        "command": "rm -rf /tmp/x",
        "pattern_key": "rm -rf",
        "description": "dangerous",
    }
    entry = approval_mod._ApprovalEntry(approval_data)
    with approval_mod._lock:
        approval_mod._gateway_queues[session_id] = [entry]
    from keprix.api import web_ui_prompt_bridge as bridge

    approval_id = "aid123"
    with bridge._lock:
        bridge._approval_ids[approval_id] = session_id

    resolved: list[str | None] = []

    def _waiter() -> None:
        entry.event.wait(timeout=2.0)
        resolved.append(entry.result)

    thread = threading.Thread(target=_waiter, daemon=True)
    thread.start()
    assert respond_approval(session_id, approval_id, "once") is True
    thread.join(timeout=2.0)
    assert resolved == ["once"]


def test_clarify_respond_route(prompt_client) -> None:
    client = prompt_client
    session_id = client.post("/api/conversations", json={"title": "Prompt test"}).json()["id"]
    clarify_mod.register(
        clarify_id="route-cid",
        session_key=session_id,
        question="Choose",
        choices=["one"],
    )
    response = client.post(
        f"/api/conversations/{session_id}/clarify/route-cid/respond",
        json={"answer": "one"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_approval_respond_route_conflict_when_not_pending(prompt_client) -> None:
    client = prompt_client
    session_id = client.post("/api/conversations", json={"title": "Prompt test"}).json()["id"]
    response = client.post(
        f"/api/conversations/{session_id}/approval/missing-id/respond",
        json={"decision": "deny"},
    )
    assert response.status_code == 409
