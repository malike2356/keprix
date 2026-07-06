"""Credential setup API tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.security.vault_service import reset_vault_service
from keprix.setup.audit import reset_setup_audit
from keprix.setup.runtime_config import RuntimeConfigStore, reset_runtime_config


@pytest.fixture
def setup_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    reset_vault_service()
    reset_setup_audit()
    reset_runtime_config()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    runtime = RuntimeConfigStore(str(tmp_path / "runtime_config.json"))
    monkeypatch.setattr("keprix.setup.runtime_config.get_runtime_config", lambda: runtime)
    monkeypatch.setattr("keprix.setup.routes.get_runtime_config", lambda: runtime)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, runtime


def test_catalog_lists_openai(setup_client):
    client, _runtime = setup_client
    catalog = client.get("/api/setup/catalog")
    assert catalog.status_code == 200
    assert any(item["id"] == "openai" for item in catalog.json()["items"])


def test_secure_input_enables_valid_openai_key(setup_client):
    client, runtime = setup_client
    response = client.post(
        "/api/setup/secure-input",
        json={"service_id": "openai", "fields": {"api_key": "sk-test-openai-key"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert runtime.status()["openai"]["enabled"] is True


def test_invalid_credentials_not_enabled(setup_client):
    client, runtime = setup_client
    response = client.post(
        "/api/setup/secure-input",
        json={"service_id": "openai", "fields": {"api_key": "invalid-key"}},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert runtime.status().get("openai", {}).get("enabled") is not True

    audit = client.get("/api/setup/audit")
    blob = json.dumps(audit.json())
    assert "invalid-key" not in blob


def test_disable_service(setup_client):
    client, runtime = setup_client
    client.post(
        "/api/setup/secure-input",
        json={"service_id": "openai", "fields": {"api_key": "sk-test-openai-key"}},
    )
    disabled = client.post("/api/setup/disable", json={"service_id": "openai"})
    assert disabled.status_code == 200
    assert runtime.status()["openai"]["enabled"] is False
