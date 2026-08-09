"""Lifecycle hooks that enqueue index/deindex jobs (Prompt 652)."""

from __future__ import annotations

from typing import Any

from keprix.document_vault.search.policy import should_index_item
from keprix.document_vault.store import DocumentVaultStore


def on_item_written(
    store: DocumentVaultStore,
    workspace_id: str,
    item: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not item:
        return None
    item_id = str(item.get("id") or "")
    rev = int(item.get("current_revision") or 0)
    if should_index_item(store, workspace_id, item):
        return store.enqueue_job(
            workspace_id,
            "index_item",
            item_id=item_id,
            idempotency_key=f"index:{item_id}:r{rev}",
            payload={"item_id": item_id, "revision": rev},
        )
    return store.enqueue_job(
        workspace_id,
        "deindex_item",
        item_id=item_id,
        idempotency_key=f"deindex:{item_id}:write",
        payload={"item_id": item_id, "reason": "policy_skip"},
    )


def on_item_trashed_or_deleted(
    store: DocumentVaultStore,
    workspace_id: str,
    item_id: str,
    *,
    reason: str,
) -> dict[str, Any]:
    return store.enqueue_job(
        workspace_id,
        "deindex_item",
        item_id=item_id,
        idempotency_key=f"deindex:{item_id}:{reason}",
        payload={"item_id": item_id, "reason": reason},
    )


def on_item_restored(
    store: DocumentVaultStore,
    workspace_id: str,
    item: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return on_item_written(store, workspace_id, item)


__all__ = [
    "on_item_restored",
    "on_item_trashed_or_deleted",
    "on_item_written",
]
