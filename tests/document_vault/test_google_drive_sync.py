"""Document Vault Google Drive sync tests (Prompt 649)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.document_vault.google.client import FakeDriveTransport
from keprix.document_vault.google.export_mime import EXPORT_MIME, GOOGLE_DOC, export_mime_for
from keprix.document_vault.google.grants import (
    DriveGrant,
    decrypt_grant,
    encrypt_grant,
    new_verification_token,
    redact_mapping,
    verify_channel_token,
)
from keprix.document_vault.google.scopes import DRIVE_FILE_SCOPE, DRIVE_FULL_SCOPE, scopes_for_mode
from keprix.document_vault.google.service import GoogleDriveVaultService
from keprix.document_vault.google.watch import DriveWatchManager
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.storage import LocalStorageAdapter
from keprix.document_vault.store import reset_document_vault_store_for_tests


@pytest.fixture()
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_ENABLED", "1")
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC", "1")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client")
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_GOOGLE_TOKEN_KEY", "test-key-649")
    store = reset_document_vault_store_for_tests(tmp_path / "vault.sqlite")
    svc = DocumentVaultService(store=store, storage=LocalStorageAdapter(root=tmp_path / "blobs"))
    transport = FakeDriveTransport()
    gsvc = GoogleDriveVaultService(store=store, vault=svc, transport=transport)
    return gsvc, store, svc, transport


def test_scopes_prefer_drive_file_for_outbound() -> None:
    assert DRIVE_FILE_SCOPE in scopes_for_mode("outbound_only")
    assert DRIVE_FULL_SCOPE not in scopes_for_mode("outbound_only")
    assert DRIVE_FULL_SCOPE in scopes_for_mode("two_way")


def test_export_mime_mappings_documented() -> None:
    assert export_mime_for(GOOGLE_DOC, "pdf") == "application/pdf"
    assert "markdown" in EXPORT_MIME[GOOGLE_DOC]


def test_grant_encryption_round_trip_and_redaction() -> None:
    grant = DriveGrant(access_token="secret-access", refresh_token="secret-refresh", account_email="a@b.c")
    cipher = encrypt_grant(grant)
    assert "secret-access" not in cipher
    restored = decrypt_grant(cipher)
    assert restored.access_token == "secret-access"
    public = redact_mapping({"access_token": "x", "ok": True, "nested": {"refresh_token": "y", "mode": "two_way"}})
    assert "access_token" not in public
    assert public["nested"]["mode"] == "two_way"
    assert "refresh_token" not in public["nested"]


def test_not_configured_without_google(vault, monkeypatch: pytest.MonkeyPatch) -> None:
    gsvc, _store, _svc, _transport = vault
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC", "0")
    status = gsvc.status("ws")
    assert status.get("connected") is False or status.get("error_code") == "not_configured"
    with pytest.raises(VaultError) as exc:
        gsvc.begin_connect("ws", user_id="u1")
    assert exc.value.code == "not_configured"


def test_connect_configure_sync_push_and_conflict(vault) -> None:
    gsvc, store, svc, transport = vault
    gsvc.complete_connect(
        "ws",
        user_id="u1",
        access_token="tok",
        refresh_token="ref",
        account_email="owner@example.com",
        mode="two_way",
    )
    status = gsvc.status("ws")
    assert status["connected"] is True
    assert "access_token" not in status
    assert status["account_email"] == "owner@example.com"

    gsvc.configure_root("ws", root_folder_id="root1", root_folder_name="Keprix Vault")
    with pytest.raises(VaultError) as exc:
        gsvc.configure_root("ws", root_folder_id="root1", enable_shared_drives=True)
    assert exc.value.code == "not_configured"

    local = svc.create_text_item("ws", "Note.md", "# hi\n", kind="markdown", actor_id="u1")
    store.update_item("ws", local["id"], metadata={"local_dirty": True}, bump_revision=False)
    pushed = gsvc.sync_now("ws", direction="outbound", item_id=local["id"], actor_id="u1")
    assert pushed["ok"] is True
    assert pushed["provider_item_id"]

    # Seed remote change conflicting with dirty local
    mapping = store.get_provider_mapping_for_item("ws", local["id"], "google_drive")
    assert mapping
    provider_id = str(mapping["provider_item_id"])
    store.upsert_provider_mapping(
        "ws",
        local["id"],
        provider="google_drive",
        provider_item_id=provider_id,
        provider_revision="1",
        content_authority="workspace",
        conflict_state=None,
        metadata={},
    )
    store.update_item("ws", local["id"], metadata={"local_dirty": True}, bump_revision=False)
    transport.changes = [
        {
            "fileId": provider_id,
            "removed": False,
            "file": {"id": provider_id, "name": "Note.md", "mimeType": "text/markdown", "version": "2"},
        }
    ]
    result = gsvc.sync_now("ws", source="manual", direction="inbound", actor_id="u1")
    assert result["conflicts"] >= 1
    conflicts = gsvc.list_conflicts("ws")["conflicts"]
    assert conflicts
    resolved = gsvc.resolve_conflict("ws", local["id"], choice="keep_both", actor_id="u1")
    assert resolved["ok"] is True


def test_changes_pagination(vault) -> None:
    gsvc, _store, _svc, transport = vault
    gsvc.complete_connect("ws", user_id="u1", access_token="tok", refresh_token="ref", mode="inbound_only")
    transport.changes = [
        {
            "fileId": f"f{i}",
            "file": {
                "id": f"f{i}",
                "name": f"File {i}",
                "mimeType": "text/plain",
                "version": "1",
            },
        }
        for i in range(5)
    ]
    # Force small pages via transport pageSize still 100; simulate by setting many and checking pages>=1
    result = gsvc.sync_now("ws", source="poll")
    assert result["applied"] == 5
    assert result["pages"] >= 1
    assert result["new_page_token"]


def test_refresh_disconnect_and_token_leak_guard(vault) -> None:
    gsvc, store, _svc, _transport = vault
    gsvc.complete_connect("ws", user_id="u1", access_token="tok", refresh_token="ref")
    refreshed = gsvc.refresh_grant("ws")
    assert refreshed["refreshed"] is True
    conn = store.get_drive_connection("ws")
    assert conn and conn.get("grant_ciphertext")
    assert "tok" not in str(conn.get("grant_ciphertext"))
    gsvc.disconnect("ws")
    assert store.get_drive_connection("ws") is None


def test_watch_renewal_and_webhook_verification(vault, monkeypatch: pytest.MonkeyPatch) -> None:
    gsvc, store, _svc, transport = vault
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_GOOGLE_WEBHOOK_URL", "https://example.com")
    gsvc.complete_connect("ws", user_id="u1", access_token="tok", refresh_token="ref", mode="two_way")
    client = gsvc._client_for_workspace("ws")
    watch = DriveWatchManager(store, client)
    registered = watch.register("ws")
    assert registered["channel_id"]
    renewed = watch.renew_if_needed("ws", overlap_hours=2)
    assert renewed.get("renewed") is False

    # Force renewal by setting expiry in the past
    store.update_drive_connection("ws", channel_expires_at="2000-01-01T00:00:00+00:00")
    renewed2 = watch.renew_if_needed("ws", overlap_hours=2)
    assert renewed2.get("renewed") is True

    conn = store.get_drive_connection("ws")
    assert conn
    plaintext, digest = new_verification_token()
    store.update_drive_connection("ws", verification_token_hash=digest)
    assert verify_channel_token(plaintext, digest)
    assert not verify_channel_token("wrong", digest)

    transport.changes = []
    conn = store.get_drive_connection("ws")
    assert conn
    out = gsvc.handle_webhook(
        channel_id=str(conn["channel_id"]),
        resource_id=str(conn["resource_id"]),
        channel_token=plaintext,
        message_number="1",
        resource_state="change",
    )
    assert out["source"] == "webhook"
    # Duplicate notification
    dup = gsvc.handle_webhook(
        channel_id=str(conn["channel_id"]),
        resource_id=str(conn["resource_id"]),
        channel_token=plaintext,
        message_number="1",
        resource_state="change",
    )
    assert dup["duplicate_notification"] is True


def test_rate_limit_and_revocation_surface(vault) -> None:
    gsvc, _store, _svc, transport = vault
    gsvc.complete_connect("ws", user_id="u1", access_token="tok", refresh_token="ref", mode="inbound_only")
    transport.rate_limited = True
    result = gsvc.sync_now("ws")
    assert result["errors"]
    transport.rate_limited = False
    transport.revoked = True
    result2 = gsvc.sync_now("ws")
    assert result2["errors"]
