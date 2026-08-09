"""Canonical channel attachment import pipeline (Prompt 651)."""

from __future__ import annotations

from typing import Any

from keprix.document_vault.channel.binding import resolve_channel_binding
from keprix.document_vault.channel.contract import (
    ChannelAttachment,
    ChannelReceipt,
    channel_supports_files,
)
from keprix.document_vault.channel.quarantine import quarantine_attachment
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import DocumentVaultService, get_document_vault_service
from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store


def _store(store: DocumentVaultStore | None = None) -> DocumentVaultStore:
    return store or get_document_vault_store()


def _svc(service: DocumentVaultService | None = None) -> DocumentVaultService:
    return service or get_document_vault_service()


def import_channel_attachment(
    attachment: ChannelAttachment,
    *,
    claimed_workspace_id: str | None = None,
    parent_id: str | None = None,
    store: DocumentVaultStore | None = None,
    service: DocumentVaultService | None = None,
) -> ChannelReceipt:
    """Quarantine, dedupe, and import through the canonical Document Vault job."""
    platform = str(attachment.platform or "").strip().lower()
    if not channel_supports_files(platform):
        raise VaultError("unsupported_channel", f"{platform} does not support file vault import")

    ctx = resolve_channel_binding(
        platform,
        attachment.channel_user_id,
        claimed_workspace_id=claimed_workspace_id,
        store=store,
    )

    event_id = str(attachment.event_id or "").strip()
    if not event_id:
        raise VaultError("invalid_args", "event_id required for idempotent channel import")

    st = _store(store)
    prior = st.get_channel_event(ctx.workspace_id, platform, event_id, action="import")
    if prior:
        return ChannelReceipt(
            ok=True,
            message=f"Already imported (deduplicated). item_id={prior.get('result_item_id')}",
            item_id=prior.get("result_item_id"),
            deduplicated=True,
            data=prior.get("result") or {},
        )

    dest = parent_id if parent_id is not None else attachment.parent_id
    if dest is None and _destination_ambiguous(st, ctx.workspace_id):
        raise VaultError(
            "destination_required",
            "destination folder is ambiguous; pass parent_id or /vault import --parent <id>",
        )

    quarantine = quarantine_attachment(
        attachment.data,
        filename=attachment.filename,
        declared_mime=attachment.declared_mime,
    )

    result = _svc(service).import_bytes(
        ctx.workspace_id,
        attachment.data,
        filename=attachment.filename or "upload.bin",
        declared_mime=attachment.declared_mime,
        parent_id=dest,
        actor_id=ctx.actor_id,
    )
    item = result.get("derived") or result.get("original") or {}
    item_id = item.get("id")
    job = result.get("job") or {}

    st.record_channel_event(
        ctx.workspace_id,
        platform=platform,
        event_id=event_id,
        action="import",
        result_item_id=item_id,
        result={
            "filename": attachment.filename,
            "quarantine": {"scan": quarantine.get("scan"), "spoofed": (quarantine.get("validation") or {}).get("sniff", {}).get("spoofed")},
            "job_id": job.get("id"),
            "item_id": item_id,
        },
    )
    st._audit(
        ctx.workspace_id,
        item_id=item_id,
        action="channel:import",
        actor_id=ctx.actor_id,
        payload={
            "platform": platform,
            "event_id": event_id,
            "filename": attachment.filename,
            "byte_size": attachment.byte_size,
        },
    )
    st._commit()

    return ChannelReceipt(
        ok=True,
        message=f"Imported into Document Vault. item_id={item_id}",
        item_id=item_id,
        job_id=job.get("id"),
        data={"item": item, "job": job, "workspace_id": ctx.workspace_id},
    )


def _destination_ambiguous(store: DocumentVaultStore, workspace_id: str) -> bool:
    """True when root already has multiple folders and no parent was supplied."""
    listed = store.list_items(workspace_id, parent_id=None, limit=20, offset=0)
    folders = [row for row in (listed.get("items") or []) if row.get("kind") == "folder"]
    return len(folders) > 1


__all__ = ["import_channel_attachment"]
