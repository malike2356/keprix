"""Vault security tests."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def vault_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "")
    monkeypatch.setenv("ADMIN_EMAIL", "")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_vault_item_requires_unlock(vault_client):
    client = vault_client
    create = client.post(
        "/api/vault/items",
        json={"label": "API", "value": "secret-value", "category": "api_key"},
    )
    assert create.status_code == 403

    unlock = client.post("/api/vault/unlock", json={"master_password": "vault-master"})
    assert unlock.status_code == 200

    create = client.post(
        "/api/vault/items",
        json={"label": "API", "value": "secret-value", "category": "api_key"},
    )
    assert create.status_code == 200
    item_id = create.json()["item"]["id"]

    client.post("/api/vault/lock")
    locked_get = client.get(f"/api/vault/items/{item_id}")
    assert locked_get.status_code == 403

    client.post("/api/vault/unlock", json={"master_password": "vault-master"})
    opened = client.get(f"/api/vault/items/{item_id}")
    assert opened.status_code == 200
    assert opened.json()["item"]["value"] == "secret-value"


def test_vault_value_not_in_audit_log(vault_client, caplog):
    client = vault_client
    caplog.set_level(logging.INFO)
    client.post("/api/vault/unlock", json={"master_password": "vault-master"})
    create = client.post(
        "/api/vault/items",
        json={"label": "SMTP", "value": "super-secret-password", "category": "password"},
    )
    item_id = create.json()["item"]["id"]
    client.get(f"/api/vault/items/{item_id}")

    blob = caplog.text
    assert "super-secret-password" not in blob
    assert "vault-master" not in blob
