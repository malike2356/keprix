"""Contact sync reliability tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from keprix.contacts.store import get_contact_store, reset_contact_store
from keprix.contacts.sync.base import SyncResult
from keprix.contacts.sync.carddav import CardDAVContactsConnector
from keprix.contacts.sync.scheduler import (
    get_sync_source,
    register_sync_source,
    reset_sync_sources_for_tests,
    run_sync,
    unregister_sync_source,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_contact_store()
    reset_sync_sources_for_tests()
    yield
    reset_contact_store()
    reset_sync_sources_for_tests()


@pytest.mark.asyncio
async def test_run_sync_fail_closed_keeps_error_and_does_not_advance_times():
    source = {
        "id": "src-fail",
        "user_id": "u1",
        "provider": "carddav",
        "display_name": "Broken",
        "sync_enabled": True,
        "sync_interval_minutes": 60,
        "contact_count": 0,
        "carddav_url": "https://example.test/dav",
        "carddav_username": "alice",
        "vault_token_id": "vault-1",
    }
    await register_sync_source(source)
    with patch.object(
        CardDAVContactsConnector,
        "full_sync",
        AsyncMock(return_value=SyncResult(error="CardDAV authentication failed")),
    ):
        result = await run_sync("src-fail")
    assert result.get("error")
    saved = await get_sync_source("src-fail")
    assert saved is not None
    assert saved.get("last_sync_error")
    assert saved.get("last_delta_sync_at") is None
    assert saved.get("last_full_sync_at") is None
    await unregister_sync_source("src-fail")


@pytest.mark.asyncio
async def test_carddav_password_reads_oauth_bundle():
    connector = CardDAVContactsConnector()
    source = {"vault_token_id": "v1", "user_id": "u1"}

    class FakeVault:
        async def get_oauth_bundle(self, vault_id: str, user_id: str):
            assert vault_id == "v1"
            assert user_id == "u1"
            return {"password": "app-secret"}

        async def get_item(self, *args, **kwargs):
            return None

    with patch("keprix.contacts.sync.carddav.get_vault_service", return_value=FakeVault()):
        password = await connector._password(source)
    assert password == "app-secret"


@pytest.mark.asyncio
async def test_upsert_import_is_user_scoped():
    store = get_contact_store()
    await store.upsert_import(
        {
            "display_name": "A",
            "emails": [{"address": "a@example.com", "primary": True}],
            "source_id": "1",
        },
        source="google",
        user_id="user-a",
    )
    await store.upsert_import(
        {
            "display_name": "B",
            "emails": [{"address": "a@example.com", "primary": True}],
            "source_id": "2",
        },
        source="google",
        user_id="user-b",
    )
    a_rows = await store.list_contacts(user_id="user-a")
    b_rows = await store.list_contacts(user_id="user-b")
    assert len(a_rows) == 1
    assert a_rows[0].display_name == "A"
    assert len(b_rows) == 1
    assert b_rows[0].display_name == "B"
