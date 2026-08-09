"""Operator diagnostics for Document Vault async stages (Prompt 652)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store


def build_diagnostics(
    workspace_id: str,
    *,
    store: DocumentVaultStore | None = None,
) -> dict[str, Any]:
    st = store or get_document_vault_store()
    jobs = st.list_jobs(workspace_id)
    by_status: dict[str, int] = {}
    for job in jobs:
        status = str(job.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1

    index_rows = st.list_index_entries(workspace_id)
    index_by_status: dict[str, int] = {}
    for row in index_rows:
        status = str(row.get("status") or "unknown")
        index_by_status[status] = index_by_status.get(status, 0) + 1

    drive = {}
    try:
        drive = st.get_drive_connection(workspace_id) or {}
    except Exception:
        drive = {}

    watch_expires = drive.get("channel_expires_at")
    watch_expired = False
    if watch_expires:
        try:
            exp = datetime.fromisoformat(str(watch_expires).replace("Z", "+00:00"))
            watch_expired = exp <= datetime.now(timezone.utc)
        except Exception:
            watch_expired = False

    orphans = st.scan_orphan_index_entries(workspace_id)
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "jobs": {
            "total": len(jobs),
            "by_status": by_status,
            "dead_letters": by_status.get("dead_letter", 0),
            "queued": by_status.get("queued", 0),
            "running": by_status.get("running", 0),
        },
        "index": {
            "total": len(index_rows),
            "by_status": index_by_status,
            "lag_pending": index_by_status.get("pending", 0) + by_status.get("queued", 0),
            "errors": index_by_status.get("error", 0),
        },
        "google": {
            "connected": bool(drive.get("connected")),
            "last_error": drive.get("last_error"),
            "last_sync_at": drive.get("last_sync_at"),
            "watch_expires_at": watch_expires,
            "watch_expired": watch_expired,
            "oauth_failure": bool(drive.get("last_error")),
        },
        "orphans": {
            "index_entries_without_item": len(orphans),
            "sample": orphans[:10],
        },
        "malware_hook": {"engine": "noop", "note": "operator replaceable"},
    }


__all__ = ["build_diagnostics"]
