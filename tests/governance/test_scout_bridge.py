"""Tests for Prompt 38: Scout governance bridge."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.governance.kill_relay import agent_stop_requested, apply_kill_directive, clear_kill_state
from keprix.governance.policy_receiver import get_policy_registry, reload_policies
from keprix.governance.signing import sign_payload
from keprix.governance.store import GovernanceStore
from keprix.security.rate_limiter import reset_rate_limits
from keprix.security.vault_service import reset_vault_service


@pytest.fixture
def scout_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    reset_vault_service()

    store = GovernanceStore(base_dir=tmp_path / "scout")
    monkeypatch.setattr("keprix.governance.store.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.governance.client.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.governance.event_reporter.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.governance.heartbeat.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.governance.policy_receiver.get_governance_store", lambda: store)
    monkeypatch.setattr("keprix.governance.routes.get_governance_store", lambda: store)

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    async def fake_enroll(**_kwargs):
        return "instance-test-123"

    monkeypatch.setattr("keprix.governance.enrollment.enroll_instance", fake_enroll)
    monkeypatch.setattr("keprix.governance.client.enroll_instance", fake_enroll)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, store


def test_connect_stores_api_key_in_vault_not_config(scout_client):
    client, store = scout_client
    response = client.post(
        "/api/governance/connect",
        json={"provider_endpoint": "https://scout.example.test", "api_key": "scout-secret-key-12345"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["config"]["enabled"] is True
    assert body["config"]["instance_id"] == "instance-test-123"
    assert body["config"]["enrolled_at"]
    assert body["config"]["api_key_vault_id"]
    config_text = (store._config_path).read_text(encoding="utf-8")
    assert "scout-secret-key-12345" not in config_text


def test_disabled_scout_skips_heartbeat(scout_client):
    client, _store = scout_client
    response = client.post("/api/governance/heartbeat")
    assert response.status_code == 200
    assert response.json()["skipped"] is True


def test_tool_block_policy_applied_quickly(scout_client):
    clear_kill_state()
    get_policy_registry().reload_from_store([])
    client, _store = scout_client
    client.post(
        "/api/governance/connect",
        json={"provider_endpoint": "https://scout.example.test", "api_key": "scout-secret-key-12345"},
    )
    api_key = "scout-secret-key-12345"
    payload = {
        "type": "policy",
        "policy_type": "tool_block",
        "policy_value": {"tool_name": "read_file"},
    }
    body = json.dumps(payload).encode("utf-8")
    signature = f"sha256={sign_payload(api_key, body)}"
    webhook = client.post(
        "/api/governance/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Governance-Signature": signature},
    )
    assert webhook.status_code == 200
    assert get_policy_registry().is_tool_blocked("read_file") is True


def test_stop_agent_kill_directive(scout_client):
    clear_kill_state()
    client, _store = scout_client
    client.post(
        "/api/governance/connect",
        json={"provider_endpoint": "https://scout.example.test", "api_key": "scout-secret-key-12345"},
    )
    api_key = "scout-secret-key-12345"
    payload = {"type": "kill", "directive_type": "stop_agent", "payload": {}}
    body = json.dumps(payload).encode("utf-8")
    signature = f"sha256={sign_payload(api_key, body)}"
    webhook = client.post(
        "/api/governance/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Governance-Signature": signature},
    )
    assert webhook.status_code == 200
    assert agent_stop_requested() is True


def test_disconnect_requires_acceptance(scout_client):
    client, _store = scout_client
    client.post(
        "/api/governance/connect",
        json={"provider_endpoint": "https://scout.example.test", "api_key": "scout-secret-key-12345"},
    )
    denied = client.post("/api/governance/disconnect", json={"accept_responsibility": False})
    assert denied.status_code == 400
    accepted = client.post("/api/governance/disconnect", json={"accept_responsibility": True})
    assert accepted.status_code == 200
    assert accepted.json()["config"]["enabled"] is False


@pytest.mark.asyncio
async def test_heartbeat_updates_status_when_enabled(scout_client, monkeypatch):
    client, store = scout_client
    client.post(
        "/api/governance/connect",
        json={"provider_endpoint": "https://scout.example.test", "api_key": "scout-secret-key-12345"},
    )

    async def fake_send(**_kwargs):
        from datetime import datetime, timezone

        await store.save_config(
            {
                "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat_ok": True,
            }
        )
        return {"ok": True, "status_code": 200}

    monkeypatch.setattr("keprix.governance.heartbeat.send_heartbeat", fake_send)
    response = client.post("/api/governance/heartbeat")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    cfg = await store.get_config()
    assert cfg["last_heartbeat_ok"] is True
    assert cfg["last_heartbeat_at"]


@pytest.mark.asyncio
async def test_reload_policies_from_store(scout_client):
    _client, store = scout_client
    await store.add_policy("feature_flag", {"name": "mutation_engine", "enabled": False})
    await reload_policies()
    assert get_policy_registry().feature_enabled("mutation_engine", default=True) is False
