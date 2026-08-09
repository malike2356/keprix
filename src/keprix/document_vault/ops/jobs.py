"""Durable Document Vault job lifecycle (Prompt 652)."""

from __future__ import annotations

from typing import Any, Callable

from keprix.document_vault.models import VaultError
from keprix.document_vault.search.indexer import VaultContentIndexer
from keprix.document_vault.service import DocumentVaultService, get_document_vault_service
from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store


def claim_next_job(
    store: DocumentVaultStore,
    workspace_id: str,
    *,
    worker_id: str = "worker",
) -> dict[str, Any] | None:
    return store.claim_job(workspace_id, worker_id=worker_id)


def complete_job(
    store: DocumentVaultStore,
    workspace_id: str,
    job_id: str,
    *,
    result: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    return store.complete_job(workspace_id, job_id, result=result or {})


def fail_job(
    store: DocumentVaultStore,
    workspace_id: str,
    job_id: str,
    *,
    reason: str,
) -> dict[str, Any] | None:
    return store.fail_job(workspace_id, job_id, reason=reason)


def retry_job(
    store: DocumentVaultStore,
    workspace_id: str,
    job_id: str,
) -> dict[str, Any]:
    row = store.retry_job(workspace_id, job_id)
    if not row:
        raise VaultError("not_found", "job not found or not retryable")
    return row


def process_job(
    store: DocumentVaultStore,
    job: dict[str, Any],
    *,
    service: DocumentVaultService | None = None,
) -> dict[str, Any]:
    """Run one claimed vault job (index/deindex/import_normalize)."""
    svc = service or get_document_vault_service(store=store)
    indexer = VaultContentIndexer(store, svc)
    kind = str(job.get("kind") or "")
    workspace_id = str(job.get("workspace_id") or "")
    item_id = str(job.get("item_id") or (job.get("payload") or {}).get("item_id") or "")
    if kind == "index_item":
        return indexer.index_item(workspace_id, item_id)
    if kind == "deindex_item":
        return indexer.deindex_item(workspace_id, item_id)
    if kind.startswith("import_") or kind.startswith("channel:"):
        return {"ok": True, "status": "noop", "kind": kind}
    return {"ok": True, "status": "ignored", "kind": kind}


def drain_jobs(
    workspace_id: str,
    *,
    limit: int = 20,
    store: DocumentVaultStore | None = None,
    service: DocumentVaultService | None = None,
    worker_id: str = "local-drain",
) -> list[dict[str, Any]]:
    st = store or get_document_vault_store()
    svc = service or get_document_vault_service(store=st)
    results: list[dict[str, Any]] = []
    for _ in range(max(1, limit)):
        job = claim_next_job(st, workspace_id, worker_id=worker_id)
        if not job:
            break
        try:
            result = process_job(st, job, service=svc)
            complete_job(st, workspace_id, job["id"], result=result)
            results.append({"job_id": job["id"], "ok": True, "result": result})
        except Exception as exc:
            fail_job(st, workspace_id, job["id"], reason=str(exc)[:500])
            results.append({"job_id": job["id"], "ok": False, "error": str(exc)})
    return results


__all__ = [
    "claim_next_job",
    "complete_job",
    "drain_jobs",
    "fail_job",
    "process_job",
    "retry_job",
]
