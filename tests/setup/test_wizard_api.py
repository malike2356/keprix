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
    monkeypatch.setattr("keprix.auth.session.auth_manager", auth)
    client = TestClient(create_app())
    monkeypatch.delenv("KEPRIX_SETUP_COMPLETE", raising=False)
    monkeypatch.delenv("KEPRIX_PUBLIC_SETUP_DISABLED", raising=False)
    monkeypatch.setenv("KEPRIX_MULTI_USER", "false")
    return client, auth, tmp_path


def test_wizard_open_when_not_complete(wizard_client):
    client, _auth, _tmp = wizard_client
    response = client.get("/api/setup/wizard")
    assert response.status_code == 200
    body = response.json()
    assert body["complete"] is False
    assert body["public_setup_disabled"] is False


def test_wizard_owner_step_works_when_multi_user_is_off(wizard_client):
    client, auth, _tmp = wizard_client
    denied = client.post("/api/auth/register", json={"username": "other", "password": "x" * 12})
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Registration disabled"

    created = client.post(
        "/api/setup/step/1",
        json={"full_name": "Laud Paul", "email": "owner@example.com", "password": "x" * 12},
    )
    assert created.status_code == 200, created.text
    owner = auth.get_user("owner@example.com")
    assert owner is not None
    assert owner["role"] == "admin"
    assert owner["display_name"] == "Laud Paul"

    login = client.post(
        "/api/auth/login",
        json={"username": "owner@example.com", "password": "x" * 12},
    )
    assert login.status_code == 200, login.text
    assert login.json()["token"]


def test_wizard_owner_step_without_env_admin_password(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("KEPRIX_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "false")
    monkeypatch.delenv("KEPRIX_SETUP_COMPLETE", raising=False)
    monkeypatch.delenv("KEPRIX_PUBLIC_SETUP_DISABLED", raising=False)
    reset_rate_limits()
    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.session.auth_manager", auth)
    client = TestClient(create_app())

    created = client.post(
        "/api/setup/step/1",
        json={"email": "solo@example.com", "password": "solo-pass-1"},
    )
    assert created.status_code == 200, created.text
    login = client.post(
        "/api/auth/login",
        json={"username": "solo@example.com", "password": "solo-pass-1"},
    )
    assert login.status_code == 200, login.text


def test_wizard_blocked_after_complete(wizard_client):
    client, _auth, tmp = wizard_client
    mark_setup_complete(owner_email="owner@example.com")
    assert is_setup_complete() is True

    denied = client.post("/api/setup/step/0", json={})
    assert denied.status_code == 403

    status = client.get("/api/setup/wizard")
    assert status.json()["complete"] is True


class TestPublicSetupDisabled:
    """The maintainer's own public marketing/demo instance
    (keprixai.com/app.keprixai.com) must never let an anonymous visitor
    create the owner account or connect an LLM provider key for it - see
    keprix.setup.wizard.is_public_setup_disabled()."""

    def test_wizard_status_reports_public_setup_disabled(self, wizard_client, monkeypatch):
        client, _auth, _tmp = wizard_client
        monkeypatch.setenv("KEPRIX_PUBLIC_SETUP_DISABLED", "1")
        response = client.get("/api/setup/wizard")
        assert response.json()["public_setup_disabled"] is True

    def test_step_blocked_even_when_setup_not_yet_complete(self, wizard_client, monkeypatch):
        """Real gap this closes: without this flag, an anonymous visitor
        to a not-yet-completed public instance could complete step 0
        (and every step after it) and become its owner. Forces the
        not-yet-complete precondition directly rather than trusting
        is_setup_complete()'s ambient state, which a sibling test file's
        own env/data-dir leakage can otherwise leave inconsistent."""
        client, _auth, tmp = wizard_client
        monkeypatch.setenv("KEPRIX_PUBLIC_SETUP_DISABLED", "1")
        marker = tmp / ".setup_complete"
        if marker.exists():
            marker.unlink()
        monkeypatch.delenv("KEPRIX_SETUP_COMPLETE", raising=False)

        denied = client.post("/api/setup/step/0", json={})
        assert denied.status_code == 403

    def test_step_still_blocked_if_completion_marker_is_ever_reset(self, wizard_client, monkeypatch):
        """Defense in depth: even if the completion marker were somehow
        cleared on the public instance, the public flag alone must still
        refuse every step - not just rely on is_setup_complete()."""
        client, _auth, tmp = wizard_client
        monkeypatch.setenv("KEPRIX_PUBLIC_SETUP_DISABLED", "1")
        marker = tmp / ".setup_complete"
        if marker.exists():
            marker.unlink()
        monkeypatch.delenv("KEPRIX_SETUP_COMPLETE", raising=False)

        denied = client.post("/api/setup/step/1", json={"email": "a@b.com", "password": "x" * 12})
        assert denied.status_code == 403
