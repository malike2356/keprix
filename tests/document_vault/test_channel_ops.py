"""Document Vault channel and Telegram ops tests (Prompt 651)."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from pathlib import Path

import pytest

from keprix.document_vault.channel.binding import (
    bind_channel_identity,
    resolve_channel_binding,
    revoke_channel_binding,
)
from keprix.document_vault.channel.commands import handle_vault_channel_command, looks_like_vault_import_caption
from keprix.document_vault.channel.contract import CHANNEL_MATRIX, ChannelAttachment, channel_supports_files
from keprix.document_vault.channel.export_delivery import plan_export_delivery
from keprix.document_vault.channel.import_pipeline import import_channel_attachment
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.storage import LocalStorageAdapter
from keprix.document_vault.store import reset_document_vault_store_for_tests
from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.store import reset_outreach_store_for_tests
from keprix.slash.schemas import SlashContext


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_ENABLED", "1")
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_CHANNEL_OPS", "1")
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_CRM_BACKEND", "sqlite")
    outreach = tmp_path / "outreach.sqlite"
    reset_outreach_store_for_tests(outreach)
    reset_outreach_ops_store_for_tests(outreach)
    store = reset_document_vault_store_for_tests(tmp_path / "vault.sqlite")
    svc = DocumentVaultService(store=store, storage=LocalStorageAdapter(root=tmp_path / "blobs"))
    bind_channel_identity(
        workspace_id="ws-a",
        platform="telegram",
        channel_user_id="tg-user-1",
        actor_id="actor-1",
        store=store,
    )
    return store, svc


def test_channel_matrix_includes_telegram() -> None:
    assert channel_supports_files("telegram")
    assert "slack" in CHANNEL_MATRIX
    assert not channel_supports_files("sms")


def test_unbound_and_revoked_fail_closed(env) -> None:
    store, _svc = env
    with pytest.raises(VaultError) as exc:
        resolve_channel_binding("telegram", "unknown-user", store=store)
    assert exc.value.code == "channel_unbound"

    revoke_channel_binding("telegram", "tg-user-1", store=store)
    with pytest.raises(VaultError) as exc2:
        resolve_channel_binding("telegram", "tg-user-1", store=store)
    assert exc2.value.code == "channel_revoked"


def test_import_deduplicates_same_event(env) -> None:
    store, svc = env
    data = b"# hello vault\n"
    att = ChannelAttachment(
        platform="telegram",
        channel_user_id="tg-user-1",
        event_id="msg-100",
        filename="note.md",
        data=data,
        declared_mime="text/markdown",
    )
    first = import_channel_attachment(att, store=store, service=svc)
    assert first.ok and first.item_id and not first.deduplicated
    second = import_channel_attachment(att, store=store, service=svc)
    assert second.ok and second.deduplicated
    assert second.item_id == first.item_id


def test_mime_spoof_rejected(env) -> None:
    store, svc = env
    # PDF magic with .txt name and text/plain declaration should spoof
    data = b"%PDF-1.4 fake"
    att = ChannelAttachment(
        platform="telegram",
        channel_user_id="tg-user-1",
        event_id="msg-spoof",
        filename="readme.txt",
        data=data,
        declared_mime="text/plain",
    )
    with pytest.raises(VaultError) as exc:
        import_channel_attachment(att, store=store, service=svc)
    assert exc.value.code in {"unsupported_kind", "malware_detected"}


def test_oversized_rejected(env, monkeypatch: pytest.MonkeyPatch) -> None:
    store, svc = env
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_MAX_UPLOAD_BYTES", "32")
    att = ChannelAttachment(
        platform="telegram",
        channel_user_id="tg-user-1",
        event_id="msg-big",
        filename="big.md",
        data=b"x" * 64,
        declared_mime="text/markdown",
    )
    with pytest.raises(VaultError) as exc:
        import_channel_attachment(att, store=store, service=svc)
    assert exc.value.code == "quota_exceeded"


def test_cross_user_cannot_use_other_binding(env) -> None:
    store, svc = env
    att = ChannelAttachment(
        platform="telegram",
        channel_user_id="tg-user-OTHER",
        event_id="msg-x",
        filename="x.md",
        data=b"x",
        declared_mime="text/markdown",
    )
    with pytest.raises(VaultError) as exc:
        import_channel_attachment(att, store=store, service=svc)
    assert exc.value.code == "channel_unbound"


def test_export_attach_vs_url(env) -> None:
    store, svc = env
    created = svc.create_text_item("ws-a", "small.md", "hi", kind="markdown", actor_id="actor-1")
    ctx = resolve_channel_binding("telegram", "tg-user-1", store=store)
    planned = plan_export_delivery(ctx, created["id"], fmt="markdown", store=store, service=svc)
    assert planned["ok"] is True
    assert planned["mode"] == "attach"
    assert planned["content_base64"]

    # Force URL mode by classifying as secret (Soft Wall blocks first)
    store.update_item("ws-a", created["id"], classification="secret", bump_revision=False)
    blocked = plan_export_delivery(ctx, created["id"], fmt="markdown", store=store, service=svc)
    assert blocked.get("blocked") is True


def test_delivery_token_consume(env) -> None:
    store, svc = env
    created = svc.create_text_item("ws-a", "url.md", "body", kind="markdown", actor_id="actor-1")
    # Tiny channel limit simulation: use email max and huge content via URL path by
    # setting classification internal but forcing mode via monkeypatch of max bytes.
    ctx = resolve_channel_binding("telegram", "tg-user-1", store=store)
    # Manually create token
    token = "test-token-value"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    store.create_delivery_token("ws-a", item_id=created["id"], token_hash=token_hash, expires_at="2099-01-01T00:00:00+00:00")
    row = store.consume_delivery_token(token_hash)
    assert row and row["item_id"] == created["id"]
    assert store.consume_delivery_token(token_hash) is None


def test_slash_vault_list_and_create(env) -> None:
    _store, _svc = env

    async def _run():
        ctx = SlashContext(
            user_id="actor-1",
            workspace_id="ignored-should-not-matter",
            channel="telegram",
            channel_user_id="tg-user-1",
            raw_text="/vault create hello.md hello world",
            command="vault",
            args=["create", "hello.md", "hello", "world"],
            role="operator",
        )
        created = await handle_vault_channel_command(ctx)
        assert created.ok, created.message
        listed = await handle_vault_channel_command(
            SlashContext(
                user_id="actor-1",
                workspace_id="bogus",
                channel="telegram",
                channel_user_id="tg-user-1",
                raw_text="/vault list",
                command="vault",
                args=["list"],
                role="viewer",
            )
        )
        assert listed.ok
        assert "hello.md" in listed.message

    asyncio.run(_run())


def test_slash_unbound_denied(env) -> None:
    async def _run():
        result = await handle_vault_channel_command(
            SlashContext(
                user_id="stranger",
                workspace_id="ws-a",
                channel="telegram",
                channel_user_id="no-binding",
                raw_text="/vault list",
                command="vault",
                args=["list"],
                role="viewer",
            )
        )
        assert result.ok is False
        assert "channel_unbound" in result.message

    asyncio.run(_run())


def test_import_caption_detection() -> None:
    assert looks_like_vault_import_caption("/vault import")
    assert looks_like_vault_import_caption("please save this to vault")
    assert not looks_like_vault_import_caption("hello")


def test_slash_import_with_metadata(env) -> None:
    async def _run():
        data = base64.b64encode(b"# from telegram\n").decode()
        result = await handle_vault_channel_command(
            SlashContext(
                user_id="actor-1",
                workspace_id="ws-a",
                channel="telegram",
                channel_user_id="tg-user-1",
                raw_text="/vault import",
                command="vault",
                args=["import"],
                role="operator",
                metadata={
                    "event_id": "tg-msg-9",
                    "attachment_base64": data,
                    "attachment_filename": "from-tg.md",
                    "mime": "text/markdown",
                },
            )
        )
        assert result.ok, result.message
        assert result.data.get("item_id")

    asyncio.run(_run())
