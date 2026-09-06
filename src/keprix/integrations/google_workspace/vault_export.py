"""Create Google Workspace artifacts from Document Vault text items."""

from __future__ import annotations

from typing import Any

from keprix.document_vault.service import DocumentVaultService

from .bridge import GoogleWorkspaceBridge


def create_doc_from_vault(
    workspace_id: str,
    item_id: str,
    *,
    actor_id: str | None = None,
    confirm: bool = False,
    vault: DocumentVaultService | None = None,
    bridge: GoogleWorkspaceBridge | None = None,
) -> dict[str, Any]:
    service = vault or DocumentVaultService()
    item = service.store.get_item(workspace_id, item_id, include_trashed=False)
    if not item:
        raise ValueError("Vault item not found")
    result = (bridge or GoogleWorkspaceBridge()).docs_create(
        str(item.get("name") or "Untitled"), service.read_text(workspace_id, item_id), confirm
    )
    if result.get("document_id") or result.get("id"):
        metadata = dict(item.get("metadata") or {})
        metadata["google_doc"] = {
            "id": result.get("document_id") or result.get("id"),
            "url": result.get("url"),
        }
        service.store.update_item(
            workspace_id, item_id, metadata=metadata, actor_id=actor_id, bump_revision=False
        )
    return result


def create_slides_from_vault(
    workspace_id: str,
    item_id: str,
    *,
    actor_id: str | None = None,
    confirm: bool = False,
    vault: DocumentVaultService | None = None,
    bridge: GoogleWorkspaceBridge | None = None,
) -> dict[str, Any]:
    service = vault or DocumentVaultService()
    item = service.store.get_item(workspace_id, item_id, include_trashed=False)
    if not item:
        raise ValueError("Vault item not found")
    slides = [
        part.strip()
        for part in service.read_text(workspace_id, item_id).split("\n\n")
        if part.strip()
    ]
    result = (bridge or GoogleWorkspaceBridge()).slides_create(
        str(item.get("name") or "Untitled"), slides, confirm
    )
    if result.get("presentation_id") or result.get("id"):
        metadata = dict(item.get("metadata") or {})
        metadata["google_slides"] = {
            "id": result.get("presentation_id") or result.get("id"),
            "url": result.get("url"),
        }
        service.store.update_item(
            workspace_id, item_id, metadata=metadata, actor_id=actor_id, bump_revision=False
        )
    return result
