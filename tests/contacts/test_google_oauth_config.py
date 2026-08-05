"""Google Contacts OAuth BYOK config tests."""

from __future__ import annotations

import pytest

from keprix.contacts.google_oauth_config import (
    clear_google_oauth_app,
    get_google_oauth_app,
    public_google_oauth_status,
    save_google_oauth_app,
)
from keprix.security.vault_service import reset_vault_service


@pytest.fixture(autouse=True)
def _reset_vault(monkeypatch):
    reset_vault_service()
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("KEPRIX_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("KEPRIX_GOOGLE_CLIENT_SECRET", raising=False)
    yield
    reset_vault_service()


@pytest.mark.asyncio
async def test_save_and_resolve_google_oauth_app():
    status = await save_google_oauth_app(
        "user-1",
        "420319712907-example.apps.googleusercontent.com",
        "GOCSPX-test-secret",
    )
    assert status["configured"] is True
    assert status["source"] == "user"
    assert status["client_id_masked"].startswith("4203197129")
    assert "GOCSPX-test-secret" not in status["client_id_masked"]
    assert "client_secret" not in status

    full = await get_google_oauth_app("user-1")
    assert full["client_id"].startswith("420319712907")
    assert full["client_secret"] == "GOCSPX-test-secret"
    assert "/api/contacts/sync/google/callback" in full["redirect_uri"]

    cleared = await clear_google_oauth_app("user-1")
    assert cleared["configured"] is False


@pytest.mark.asyncio
async def test_env_fallback_when_no_user_creds(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "env-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "env-secret")
    full = await get_google_oauth_app("user-2")
    assert full["configured"] is True
    assert full["source"] == "env"
    pub = public_google_oauth_status(full)
    assert pub["configured"] is True
    assert "client_secret" not in pub
