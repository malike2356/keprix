"""Tests for conversation steer/interrupt control plane (Prompt 201)."""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.api.turn_registry import NotBusyError, turn_registry
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.workspace.repository import WorkspaceRepository


class _StubAgent:
    def __init__(self) -> None:
        self._pending_steer: str | None = None
        self._pending_steer_lock = threading.Lock()
        self._interrupt_requested = False
        self.steer_calls: list[str] = []
        self.interrupt_calls = 0

    def steer(self, text: str) -> bool:
        cleaned = text.strip()
        if not cleaned:
            return False
        with self._pending_steer_lock:
            if self._pending_steer:
                self._pending_steer = self._pending_steer + "\n" + cleaned
            else:
                self._pending_steer = cleaned
        self.steer_calls.append(cleaned)
        return True

    def interrupt(self) -> None:
        self._interrupt_requested = True
        self.interrupt_calls += 1


@pytest.fixture
def steer_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    repo = WorkspaceRepository()
    monkeypatch.setattr("keprix.workspace.repository.workspace_repo", repo)
    monkeypatch.setattr("keprix.api.conversation_routes.workspace_repo", repo)

    turn_registry._turns.clear()

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_turn_status_idle(steer_client) -> None:
    client = steer_client
    session_id = client.post("/api/conversations", json={"title": "Steer test"}).json()["id"]
    response = client.get(f"/api/conversations/{session_id}/turn-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["busy"] is False
    assert payload["mode"] in {"interrupt", "queue", "steer"}
    assert payload["queue_depth"] == 0
    assert payload["partial_chars"] == 0


def test_steer_returns_409_when_not_busy(steer_client) -> None:
    client = steer_client
    session_id = client.post("/api/conversations", json={"title": "Steer test"}).json()["id"]
    response = client.post(
        f"/api/conversations/{session_id}/steer",
        json={"text": "Focus on nginx only"},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "not_busy"


def test_steer_injects_pending_text_on_active_agent(steer_client) -> None:
    client = steer_client
    session_id = client.post("/api/conversations", json={"title": "Steer test"}).json()["id"]
    agent = _StubAgent()
    turn_registry.register(session_id)
    turn_registry.attach_agent(session_id, agent)

    try:
        response = client.post(
            f"/api/conversations/{session_id}/steer",
            json={"text": "Focus on nginx only"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert agent._pending_steer == "Focus on nginx only"
        assert agent.steer_calls == ["Focus on nginx only"]

        status = client.get(f"/api/conversations/{session_id}/turn-status").json()
        assert status["busy"] is True
    finally:
        turn_registry.unregister(session_id)


def test_interrupt_signals_active_agent(steer_client) -> None:
    client = steer_client
    session_id = client.post("/api/conversations", json={"title": "Steer test"}).json()["id"]
    agent = _StubAgent()
    turn = turn_registry.register(session_id)
    turn_registry.attach_agent(session_id, agent)

    try:
        response = client.post(f"/api/conversations/{session_id}/interrupt", json={})
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert agent.interrupt_calls == 1
        assert turn.cancel_event.is_set()
    finally:
        turn_registry.unregister(session_id)


def test_registry_does_not_leak_after_unregister() -> None:
    turn_registry.register("leak-test")
    turn_registry.unregister("leak-test")
    assert turn_registry.get("leak-test") is None


def test_turn_registry_steer_raises_not_busy() -> None:
    with pytest.raises(NotBusyError):
        turn_registry.steer("missing-session", "hello")


def test_tui_config_exposes_busy_modes(steer_client) -> None:
    client = steer_client
    response = client.get("/api/tui/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["busy_input_mode"] in {"interrupt", "queue", "steer"}
    assert set(payload["busy_input_modes"]) == {"interrupt", "queue", "steer"}
