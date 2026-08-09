"""Repair helpers for orphan index entries and rematch (Prompt 652)."""

from __future__ import annotations

from typing import Any

from keprix.document_vault.ops.jobs import drain_jobs
from keprix.document_vault.search.indexer import VaultContentIndexer
from keprix.document_vault.service import DocumentVaultService, get_document_vault_service
from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store


def repair_orphan_index_entries(
    workspace_id: str,
    *,
    dry_run: bool = True,
    store: DocumentVaultStore | None = None,
) -> dict[str, Any]:
    st = store or get_document_vault_store()
    orphans = st.scan_orphan_index_entries(workspace_id)
    removed: list[str] = []
    if not dry_run:
        for row in orphans:
            item_id = str(row.get("item_id") or "")
            if item_id:
                st.delete_index_for_item(workspace_id, item_id)
                removed.append(item_id)
    return {
        "ok": True,
        "dry_run": dry_run,
        "orphan_count": len(orphans),
        "removed": removed,
        "sample": orphans[:20],
    }


def reindex_item(
    workspace_id: str,
    item_id: str,
    *,
    store: DocumentVaultStore | None = None,
    service: DocumentVaultService | None = None,
    drain: bool = True,
) -> dict[str, Any]:
    st = store or get_document_vault_store()
    svc = service or get_document_vault_service(store=st)
    item = st.get_item(workspace_id, item_id, include_trashed=False)
    if not item:
        return {"ok": False, "error_code": "not_found"}
    rev = int(item.get("current_revision") or 0)
    job = st.enqueue_job(
        workspace_id,
        "index_item",
        item_id=item_id,
        idempotency_key=f"reindex:{item_id}:r{rev}:{rev}",
        payload={"item_id": item_id, "revision": rev, "force": True},
    )
    drained = drain_jobs(workspace_id, limit=5, store=st, service=svc) if drain else []
    # Force synchronous index as well for operator repair.
    result = VaultContentIndexer(st, svc).index_item(workspace_id, item_id)
    return {"ok": True, "job": job, "result": result, "drained": drained}


__all__ = ["reindex_item", "repair_orphan_index_entries"]
