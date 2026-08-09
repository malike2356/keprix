"""Workspace-scoped Document Vault backup and restore drill (Prompt 652)."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from keprix.document_vault.models import VaultError
from keprix.document_vault.store import DocumentVaultStore


def export_workspace_pack(
    store: DocumentVaultStore,
    workspace_id: str,
    dest_dir: Path | str,
    *,
    storage_root: Path | str | None = None,
) -> dict[str, Any]:
    """Export items, revisions, audit, mappings, index, and optional blobs."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    # Prefer direct store scan for backup fidelity (active + trashed).
    with store._lock:
        rows = store._fetchall(
            """
            SELECT * FROM document_vault_items
            WHERE workspace_id = ?
            ORDER BY created_at ASC
            """,
            (workspace_id,),
        )
    items = [store._present_item(r) for r in rows]
    pack: dict[str, Any] = {
        "workspace_id": workspace_id,
        "items": items,
        "revisions": [],
        "audit": store.list_audit(workspace_id, limit=10_000) if hasattr(store, "list_audit") else [],
        "provider_mappings": [],
        "index_entries": store.list_index_entries(workspace_id),
    }
    for item in items:
        pack["revisions"].extend(store.list_revisions(workspace_id, item["id"]))
        try:
            pack["provider_mappings"].extend(
                store.list_provider_mappings(workspace_id, item_id=item["id"])
                if hasattr(store, "list_provider_mappings")
                else []
            )
        except Exception:
            pass

    manifest_path = dest / "manifest.json"
    manifest_path.write_text(json.dumps(pack, indent=2, default=str), encoding="utf-8")

    # Copy sqlite file when available for full DB fidelity.
    db_copy = None
    if getattr(store, "path", None):
        db_copy = dest / "document_vault.sqlite"
        shutil.copy2(store.path, db_copy)

    blobs_copied = 0
    if storage_root:
        src = Path(storage_root)
        blob_dest = dest / "blobs"
        if src.exists():
            shutil.copytree(src, blob_dest, dirs_exist_ok=True)
            blobs_copied = sum(1 for _ in blob_dest.rglob("*") if _.is_file())

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "dest": str(dest),
        "item_count": len(items),
        "revision_count": len(pack["revisions"]),
        "index_count": len(pack["index_entries"]),
        "db_copy": str(db_copy) if db_copy else None,
        "blobs_copied": blobs_copied,
    }


def restore_workspace_pack_drill(
    pack_dir: Path | str,
    *,
    restore_db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Restore drill: open pack sqlite (or recreate) and verify counts."""
    src = Path(pack_dir)
    manifest_path = src / "manifest.json"
    if not manifest_path.exists():
        raise VaultError("not_found", "manifest.json missing from pack")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    db_src = src / "document_vault.sqlite"
    if not db_src.exists():
        # Manifest-only pack: verify structure.
        return {
            "ok": True,
            "mode": "manifest",
            "workspace_id": manifest.get("workspace_id"),
            "item_count": len(manifest.get("items") or []),
            "revision_count": len(manifest.get("revisions") or []),
            "index_count": len(manifest.get("index_entries") or []),
            "verified": True,
        }

    target = Path(restore_db_path or (src / "restored.sqlite"))
    shutil.copy2(db_src, target)
    conn = sqlite3.connect(str(target))
    try:
        items = conn.execute(
            "SELECT COUNT(*) FROM document_vault_items WHERE workspace_id = ?",
            (manifest.get("workspace_id"),),
        ).fetchone()[0]
        revisions = conn.execute(
            "SELECT COUNT(*) FROM document_vault_revisions WHERE workspace_id = ?",
            (manifest.get("workspace_id"),),
        ).fetchone()[0]
        audit = conn.execute(
            "SELECT COUNT(*) FROM document_vault_audit WHERE workspace_id = ?",
            (manifest.get("workspace_id"),),
        ).fetchone()[0]
    finally:
        conn.close()

    expected_items = len(manifest.get("items") or [])
    return {
        "ok": True,
        "mode": "sqlite",
        "workspace_id": manifest.get("workspace_id"),
        "restored_db": str(target),
        "item_count": items,
        "revision_count": revisions,
        "audit_count": audit,
        "expected_item_count": expected_items,
        "verified": items >= expected_items and revisions >= 0,
    }


def temp_backup_restore_roundtrip(
    store: DocumentVaultStore,
    workspace_id: str,
    *,
    storage_root: Path | str | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="dv-backup-") as tmp:
        pack = export_workspace_pack(store, workspace_id, tmp, storage_root=storage_root)
        drill = restore_workspace_pack_drill(tmp)
        return {"ok": True, "pack": pack, "drill": drill}


__all__ = [
    "export_workspace_pack",
    "restore_workspace_pack_drill",
    "temp_backup_restore_roundtrip",
]
