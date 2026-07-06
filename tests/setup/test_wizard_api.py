"""Setup wizard API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.setup.wizard import is_setup_complete, mark_setup_complete


@pytest.fixture
def wizard_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    client = TestClient(create_app())
    return client, tmp_path


def test_wizard_open_when_not_complete(wizard_client):
    client, _tmp = wizard_client
    response = client.get("/api/setup/wizard")
    assert response.status_code == 200
    assert response.json()["complete"] is False


def test_wizard_blocked_after_complete(wizard_client):
    client, tmp = wizard_client
    mark_setup_complete(owner_email="owner@example.com")
    assert is_setup_complete() is True

    denied = client.post("/api/setup/step/0", json={})
    assert denied.status_code == 403

    status = client.get("/api/setup/wizard")
    assert status.json()["complete"] is True
