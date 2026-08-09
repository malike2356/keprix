"""Idempotent migration into Document Vault (Prompt 646).

Requires KEPRIX_DOCUMENT_VAULT_MIGRATE=1. Dry-run reports without writes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.document_vault.flags import load_flags
from keprix.document_vault.models import VaultError, format_to_kind, sha256_text
from keprix.document_vault.service import DocumentVaultService, get_document_vault_service
from keprix.document_vault.store import DocumentVaultStore


def _migrate_key(source_store: str, source_id: str) -> str:
    return f"migrate:{source_store}:{source_id}"


def migrate_workspace_documents(
    workspace_id: str,
    documents: list[dict[str, Any]],
    *,
    service: DocumentVaultService | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    flags = load_flags()
    if dry_run or not flags.migrate:
        return {
            "ok": True,
            "dry_run": True,
            "mutated": False,
            "would_migrate": len(documents),
            "note": "Set KEPRIX_DOCUMENT_VAULT_MIGRATE=1 to write",
        }

    svc = service or get_document_vault_service()
    store = svc.store
    created = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    checksums: list[dict[str, Any]] = []

    for doc in documents:
        source_id = str(doc.get("id") or "")
        if not source_id:
            errors.append({"error": "missing_id"})
            continue
        key = _migrate_key("workspace_documents", source_id)
        existing = store.get_source_mapping(workspace_id, "workspace_documents", source_id)
        content = str(doc.get("content") or "")
        chk = sha256_text(content)
        if existing:
            skipped += 1
            checksums.append({"source_id": source_id, "checksum": chk, "idempotent": True})
            continue
        try:
            kind = format_to_kind(str(doc.get("format") or "markdown"))
            item = svc.create_text_item(
                workspace_id,
                str(doc.get("title") or "Untitled"),
                content,
                kind=kind,
                actor_id="migrate",
                item_id=None,  # fresh vault id; mapping preserves source
            )
            store.upsert_source_mapping(
                workspace_id,
                source_store="workspace_documents",
                source_id=source_id,
                item_id=item["id"],
                idempotency_key=key,
                checksum=chk,
            )
            # Older versions (if provided) are appended as further recoverable revisions.
            for ver in doc.get("versions") or []:
                body = str(ver.get("content") or "")
                if not body or body == content:
                    continue
                current = store.get_item(workspace_id, item["id"])
                if not current:
                    break
                svc.write_content(
                    workspace_id,
                    item["id"],
                    body.encode("utf-8"),
                    expected_revision=int(current.get("current_revision") or 0),
                    actor_id="migrate",
                    change_summary="migrated historical version",
                )
            created += 1
            checksums.append({"source_id": source_id, "item_id": item["id"], "checksum": chk})
        except VaultError as exc:
            errors.append({"source_id": source_id, **exc.as_dict()})
        except Exception as exc:
            errors.append({"source_id": source_id, "error": str(exc)})

    return {
        "ok": not errors,
        "dry_run": False,
        "mutated": created > 0,
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "checksums": checksums,
    }


def migrate_knowledge_vault_files(
    workspace_id: str,
    files: list[dict[str, Any]],
    *,
    service: DocumentVaultService | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Migrate eligible markdown vault file dicts ``{path, content}``."""
    flags = load_flags()
    if dry_run or not flags.migrate:
        return {
            "ok": True,
            "dry_run": True,
            "mutated": False,
            "would_migrate": len(files),
        }

    svc = service or get_document_vault_service()
    store = svc.store
    folder_cache: dict[str, str] = {}
    created = 0
    skipped = 0

    def ensure_folder(rel_dir: str) -> str | None:
        if not rel_dir or rel_dir in {".", "/"}:
            return None
        if rel_dir in folder_cache:
            return folder_cache[rel_dir]
        parts = [p for p in Path(rel_dir).parts if p not in {".", "/"}]
        parent: str | None = None
        accum = []
        for part in parts:
            accum.append(part)
            key = "/".join(accum)
            if key in folder_cache:
                parent = folder_cache[key]
                continue
            folder = svc.create_folder(workspace_id, part, parent_id=parent, actor_id="migrate")
            folder_cache[key] = folder["id"]
            parent = folder["id"]
        return parent

    for row in files:
        path = str(row.get("path") or "").lstrip("/")
        if ".." in path or path.startswith("/") or "\\" in path:
            continue
        source_id = path
        key = _migrate_key("knowledge_vault", source_id)
        if store.get_source_mapping(workspace_id, "knowledge_vault", source_id):
            skipped += 1
            continue
        parent_path = str(Path(path).parent)
        parent_id = ensure_folder(parent_path)
        content = str(row.get("content") or "")
        item = svc.create_text_item(
            workspace_id,
            Path(path).name or "note.md",
            content,
            kind="markdown",
            parent_id=parent_id,
            actor_id="migrate",
        )
        store.upsert_source_mapping(
            workspace_id,
            source_store="knowledge_vault",
            source_id=source_id,
            item_id=item["id"],
            idempotency_key=key,
            checksum=sha256_text(content),
        )
        created += 1

    return {
        "ok": True,
        "dry_run": False,
        "mutated": created > 0,
        "created": created,
        "skipped": skipped,
    }


def migrate_from_workspace_repo(
    workspace_id: str,
    *,
    service: DocumentVaultService | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Pull in-memory workspace_repo documents for a user/workspace key."""
    try:
        from keprix.workspace.repository import workspace_repo
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    docs_map = getattr(workspace_repo, "documents", {}) or {}
    docs: list[dict[str, Any]] = []
    for doc_id, doc in docs_map.items():
        if not isinstance(doc, dict):
            continue
        owner = str(doc.get("user_id") or doc.get("workspace_id") or "")
        if workspace_id not in {"local", "*"} and owner and owner != workspace_id:
            continue
        row = dict(doc)
        row["id"] = str(doc_id)
        docs.append(row)
    return migrate_workspace_documents(workspace_id, docs, service=service, dry_run=dry_run)
