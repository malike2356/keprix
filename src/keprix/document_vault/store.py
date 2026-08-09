"""Document Vault store (SQLite CE + optional Postgres) Prompt 646."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.document_vault.models import (
    CONTENT_AUTHORITIES,
    INDEX_POLICIES,
    ITEM_KINDS,
    VaultError,
    extension_for,
    normalize_mime,
    sanitize_name,
)
from keprix.document_vault.schema import SQLITE_SCHEMA

_STORE: "DocumentVaultStore | None" = None
_STORE_LOCK = threading.Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, default=str, sort_keys=True)


def _json_loads(raw: Any, default: Any = None) -> Any:
    if raw is None or raw == "":
        return {} if default is None else default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {} if default is None else default


class DocumentVaultStore:
    """Workspace-scoped vault metadata store."""

    def __init__(self, path: Path | str | None = None, *, backend: str = "sqlite") -> None:
        self.backend = backend
        self._lock = threading.RLock()
        if backend == "postgres":
            from keprix.crm.pg_compat import connect_postgres

            self._conn = connect_postgres()
            self._is_pg = True
        else:
            db_path = Path(
                path
                or os.environ.get("KEPRIX_DOCUMENT_VAULT_DB_PATH")
                or Path(
                    os.environ.get("KEPRIX_DATA_DIR") or (Path.home() / ".keprix")
                )
                / "document_vault.sqlite"
            )
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.path = db_path
            self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._is_pg = False
        self._ensure_schema()

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        if self._is_pg:
            from keprix.crm.pg_compat import translate_placeholders

            sql = translate_placeholders(sql)
        return self._conn.execute(sql, params)

    def _fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        cur = self._execute(sql, params)
        row = cur.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return dict(row)
        return dict(row)

    def _fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cur = self._execute(sql, params)
        rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(dict(row) if not isinstance(row, dict) else dict(row))
        return out

    def _commit(self) -> None:
        self._conn.commit()

    def _ensure_schema(self) -> None:
        with self._lock:
            if self._is_pg:
                for stmt in _split_sql(SQLITE_SCHEMA):
                    self._execute(stmt)
            else:
                self._conn.executescript(SQLITE_SCHEMA)
            self._commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- present ---
    def _present_item(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        out = dict(row)
        out["is_favorite"] = bool(out.get("is_favorite"))
        out["metadata"] = _json_loads(out.pop("metadata_json", "{}"))
        out["trashed"] = bool(out.get("trashed_at"))
        return out

    def get_item(self, workspace_id: str, item_id: str, *, include_trashed: bool = True) -> dict[str, Any] | None:
        with self._lock:
            row = self._fetchone(
                """
                SELECT * FROM document_vault_items
                WHERE workspace_id = ? AND id = ?
                """,
                (workspace_id, item_id),
            )
        item = self._present_item(row)
        if item and not include_trashed and item.get("trashed_at"):
            return None
        return item

    def _require_item(self, workspace_id: str, item_id: str, *, include_trashed: bool = False) -> dict[str, Any]:
        item = self.get_item(workspace_id, item_id, include_trashed=include_trashed)
        if not item:
            raise VaultError("not_found", f"item {item_id} not found")
        if item["workspace_id"] != workspace_id:
            raise VaultError("workspace_mismatch")
        return item

    def _assert_parent(self, workspace_id: str, parent_id: str | None) -> None:
        if parent_id is None or parent_id == "":
            return
        parent = self.get_item(workspace_id, parent_id, include_trashed=False)
        if not parent:
            raise VaultError("not_found", "parent not found")
        if parent["kind"] != "folder":
            raise VaultError("unsupported_kind", "parent must be a folder")
        if parent.get("trashed_at"):
            raise VaultError("not_found", "parent is trashed")

    def _descendants(self, workspace_id: str, folder_id: str) -> set[str]:
        """Return all descendant ids (BFS)."""
        found: set[str] = set()
        queue = [folder_id]
        while queue:
            current = queue.pop(0)
            children = self._fetchall(
                """
                SELECT id FROM document_vault_items
                WHERE workspace_id = ? AND parent_id = ? AND trashed_at IS NULL
                """,
                (workspace_id, current),
            )
            for child in children:
                cid = str(child["id"])
                if cid in found:
                    continue
                found.add(cid)
                queue.append(cid)
        return found

    def _would_cycle(self, workspace_id: str, item_id: str, new_parent_id: str | None) -> bool:
        if not new_parent_id:
            return False
        if new_parent_id == item_id:
            return True
        return new_parent_id in self._descendants(workspace_id, item_id)

    def create_item(
        self,
        workspace_id: str,
        *,
        kind: str,
        name: str,
        parent_id: str | None = None,
        mime_type: str | None = None,
        content_authority: str = "workspace",
        storage_locator: str | None = None,
        byte_size: int = 0,
        checksum: str | None = None,
        index_policy: str = "inherit",
        classification: str = "internal",
        metadata: dict[str, Any] | None = None,
        actor_id: str | None = None,
        item_id: str | None = None,
        initial_revision: int = 0,
    ) -> dict[str, Any]:
        if kind not in ITEM_KINDS:
            raise VaultError("unsupported_kind", kind)
        if content_authority not in CONTENT_AUTHORITIES:
            raise VaultError("unsupported_kind", "bad content_authority")
        if index_policy not in INDEX_POLICIES:
            index_policy = "inherit"
        clean_name = sanitize_name(name)
        if "/" in clean_name or "\\" in clean_name:
            raise VaultError("path_traversal")
        with self._lock:
            self._assert_parent(workspace_id, parent_id)
            now = _utcnow()
            iid = item_id or str(uuid.uuid4())
            existing = self._fetchone(
                "SELECT id FROM document_vault_items WHERE workspace_id = ? AND id = ?",
                (workspace_id, iid),
            )
            if existing:
                raise VaultError("idempotent_replay", "item id exists", item_id=iid)
            self._execute(
                """
                INSERT INTO document_vault_items (
                    id, workspace_id, parent_id, kind, name, mime_type, extension,
                    content_authority, storage_locator, byte_size, checksum,
                    current_revision, created_by, updated_by, created_at, updated_at,
                    is_favorite, trashed_at, trash_parent_id, index_policy,
                    classification, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?, ?)
                """,
                (
                    iid,
                    workspace_id,
                    parent_id,
                    kind,
                    clean_name,
                    normalize_mime(kind, mime_type),
                    extension_for(kind, clean_name),
                    content_authority,
                    storage_locator,
                    int(byte_size or 0),
                    checksum,
                    int(initial_revision),
                    actor_id,
                    actor_id,
                    now,
                    now,
                    index_policy,
                    classification or "internal",
                    _json_dumps(metadata or {}),
                ),
            )
            self._audit(
                workspace_id,
                item_id=iid,
                action="create",
                actor_id=actor_id,
                payload={"kind": kind, "name": clean_name, "parent_id": parent_id},
            )
            self._commit()
        return self.get_item(workspace_id, iid)  # type: ignore[return-value]

    def list_items(
        self,
        workspace_id: str,
        *,
        parent_id: str | None = None,
        include_trashed: bool = False,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit or 100), 500))
        offset = max(0, int(offset or 0))
        clauses = ["workspace_id = ?"]
        params: list[Any] = [workspace_id]
        if include_trashed:
            clauses.append("trashed_at IS NOT NULL")
        else:
            clauses.append("trashed_at IS NULL")
            if not q:
                if parent_id is None:
                    clauses.append("parent_id IS NULL")
                else:
                    clauses.append("parent_id = ?")
                    params.append(parent_id)
            elif parent_id is not None:
                clauses.append("parent_id = ?")
                params.append(parent_id)
        if q:
            clauses.append("(lower(name) LIKE ? OR lower(mime_type) LIKE ?)")
            like = f"%{q.lower()}%"
            params.extend([like, like])
        where = " AND ".join(clauses)
        with self._lock:
            total_row = self._fetchone(
                f"SELECT COUNT(*) AS c FROM document_vault_items WHERE {where}",
                tuple(params),
            )
            rows = self._fetchall(
                f"""
                SELECT * FROM document_vault_items
                WHERE {where}
                ORDER BY CASE WHEN kind = 'folder' THEN 0 ELSE 1 END, lower(name) ASC
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            )
        items = [self._present_item(r) for r in rows]
        return {
            "workspace_id": workspace_id,
            "parent_id": parent_id,
            "items": items,
            "count": len(items),
            "total": int((total_row or {}).get("c") or 0),
            "limit": limit,
            "offset": offset,
        }

    def search(
        self,
        workspace_id: str,
        query: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self.list_items(
            workspace_id,
            parent_id=None,
            include_trashed=False,
            q=query,
            limit=limit,
            offset=offset,
        )

    def update_item(
        self,
        workspace_id: str,
        item_id: str,
        *,
        expected_revision: int | None = None,
        name: str | None = None,
        storage_locator: str | None = None,
        byte_size: int | None = None,
        checksum: str | None = None,
        bump_revision: bool = False,
        change_summary: str | None = None,
        is_favorite: bool | None = None,
        index_policy: str | None = None,
        classification: str | None = None,
        metadata: dict[str, Any] | None = None,
        actor_id: str | None = None,
        content_authority: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            item = self._require_item(workspace_id, item_id, include_trashed=False)
            current_rev = int(item.get("current_revision") or 0)
            if expected_revision is not None and int(expected_revision) != current_rev:
                raise VaultError(
                    "stale_revision",
                    "expected revision mismatch",
                    expected=expected_revision,
                    current=current_rev,
                )
            new_rev = current_rev + 1 if bump_revision else current_rev
            clean_name = sanitize_name(name) if name is not None else item["name"]
            meta = metadata if metadata is not None else item.get("metadata") or {}
            now = _utcnow()
            locator = storage_locator if storage_locator is not None else item.get("storage_locator")
            size = int(byte_size) if byte_size is not None else int(item.get("byte_size") or 0)
            chk = checksum if checksum is not None else item.get("checksum")
            fav = int(item.get("is_favorite") or 0) if is_favorite is None else (1 if is_favorite else 0)
            policy = index_policy or item.get("index_policy") or "inherit"
            klass = classification or item.get("classification") or "internal"
            authority = content_authority or item.get("content_authority") or "workspace"
            self._execute(
                """
                UPDATE document_vault_items SET
                    name = ?, storage_locator = ?, byte_size = ?, checksum = ?,
                    current_revision = ?, updated_by = ?, updated_at = ?,
                    is_favorite = ?, index_policy = ?, classification = ?,
                    content_authority = ?, metadata_json = ?,
                    mime_type = ?, extension = ?
                WHERE workspace_id = ? AND id = ?
                """,
                (
                    clean_name,
                    locator,
                    size,
                    chk,
                    new_rev,
                    actor_id,
                    now,
                    fav,
                    policy,
                    klass,
                    authority,
                    _json_dumps(meta),
                    normalize_mime(item["kind"], item.get("mime_type")),
                    extension_for(item["kind"], clean_name),
                    workspace_id,
                    item_id,
                ),
            )
            if bump_revision:
                self._execute(
                    """
                    INSERT INTO document_vault_revisions (
                        id, workspace_id, item_id, revision, storage_locator,
                        byte_size, checksum, change_summary, created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        workspace_id,
                        item_id,
                        new_rev,
                        locator,
                        size,
                        chk,
                        change_summary or "update",
                        actor_id,
                        now,
                    ),
                )
            self._audit(
                workspace_id,
                item_id=item_id,
                action="update",
                actor_id=actor_id,
                payload={"revision": new_rev, "bump": bump_revision},
            )
            self._commit()
        return self.get_item(workspace_id, item_id)  # type: ignore[return-value]

    def rename(self, workspace_id: str, item_id: str, name: str, *, actor_id: str | None = None) -> dict[str, Any]:
        return self.update_item(workspace_id, item_id, name=name, actor_id=actor_id, bump_revision=False)

    def move(
        self,
        workspace_id: str,
        item_id: str,
        new_parent_id: str | None,
        *,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._require_item(workspace_id, item_id, include_trashed=False)
            self._assert_parent(workspace_id, new_parent_id)
            if self._would_cycle(workspace_id, item_id, new_parent_id):
                raise VaultError("cycle_rejected")
            now = _utcnow()
            self._execute(
                """
                UPDATE document_vault_items
                SET parent_id = ?, updated_by = ?, updated_at = ?
                WHERE workspace_id = ? AND id = ?
                """,
                (new_parent_id, actor_id, now, workspace_id, item_id),
            )
            self._audit(
                workspace_id,
                item_id=item_id,
                action="move",
                actor_id=actor_id,
                payload={"parent_id": new_parent_id},
            )
            self._commit()
        return self.get_item(workspace_id, item_id)  # type: ignore[return-value]

    def copy(
        self,
        workspace_id: str,
        item_id: str,
        *,
        new_parent_id: str | None = None,
        new_name: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        src = self._require_item(workspace_id, item_id, include_trashed=False)
        parent = new_parent_id if new_parent_id is not None else src.get("parent_id")
        return self.create_item(
            workspace_id,
            kind=src["kind"],
            name=new_name or f"{src['name']} (copy)",
            parent_id=parent,
            mime_type=src.get("mime_type"),
            content_authority=src.get("content_authority") or "workspace",
            storage_locator=src.get("storage_locator"),
            byte_size=int(src.get("byte_size") or 0),
            checksum=src.get("checksum"),
            index_policy=src.get("index_policy") or "inherit",
            classification=src.get("classification") or "internal",
            metadata={**(src.get("metadata") or {}), "copied_from": item_id},
            actor_id=actor_id,
            initial_revision=int(src.get("current_revision") or 0),
        )

    def trash(self, workspace_id: str, item_id: str, *, actor_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            item = self._require_item(workspace_id, item_id, include_trashed=False)
            now = _utcnow()
            # Trash descendants first
            desc = self._descendants(workspace_id, item_id)
            targets = [item_id, *desc]
            for tid in targets:
                row = self._fetchone(
                    "SELECT parent_id FROM document_vault_items WHERE workspace_id = ? AND id = ?",
                    (workspace_id, tid),
                )
                self._execute(
                    """
                    UPDATE document_vault_items
                    SET trashed_at = ?, trash_parent_id = COALESCE(trash_parent_id, parent_id),
                        parent_id = NULL, updated_by = ?, updated_at = ?
                    WHERE workspace_id = ? AND id = ? AND trashed_at IS NULL
                    """,
                    (now, actor_id, now, workspace_id, tid),
                )
            self._audit(
                workspace_id,
                item_id=item_id,
                action="trash",
                actor_id=actor_id,
                payload={"count": len(targets)},
            )
            self._commit()
        return self.get_item(workspace_id, item_id, include_trashed=True)  # type: ignore[return-value]

    def restore(self, workspace_id: str, item_id: str, *, actor_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            item = self.get_item(workspace_id, item_id, include_trashed=True)
            if not item or not item.get("trashed_at"):
                raise VaultError("not_found", "trashed item not found")
            parent_id = item.get("trash_parent_id")
            # If parent missing/trashed, restore to root
            if parent_id:
                parent = self.get_item(workspace_id, str(parent_id), include_trashed=False)
                if not parent or parent.get("kind") != "folder":
                    parent_id = None
            now = _utcnow()
            self._execute(
                """
                UPDATE document_vault_items
                SET trashed_at = NULL, parent_id = ?, trash_parent_id = NULL,
                    updated_by = ?, updated_at = ?
                WHERE workspace_id = ? AND id = ?
                """,
                (parent_id, actor_id, now, workspace_id, item_id),
            )
            self._audit(
                workspace_id,
                item_id=item_id,
                action="restore",
                actor_id=actor_id,
                payload={"parent_id": parent_id},
            )
            self._commit()
        return self.get_item(workspace_id, item_id)  # type: ignore[return-value]

    def permanent_delete(self, workspace_id: str, item_id: str, *, actor_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            item = self.get_item(workspace_id, item_id, include_trashed=True)
            if not item:
                raise VaultError("not_found")
            if not item.get("trashed_at"):
                raise VaultError("soft_wall_required", "trash before permanent delete")
            self._execute(
                "DELETE FROM document_vault_revisions WHERE workspace_id = ? AND item_id = ?",
                (workspace_id, item_id),
            )
            self._execute(
                "DELETE FROM document_vault_provider_mappings WHERE workspace_id = ? AND item_id = ?",
                (workspace_id, item_id),
            )
            self._execute(
                "DELETE FROM document_vault_items WHERE workspace_id = ? AND id = ?",
                (workspace_id, item_id),
            )
            self._audit(
                workspace_id,
                item_id=item_id,
                action="permanent_delete",
                actor_id=actor_id,
                payload={},
            )
            self._commit()
        return {"ok": True, "item_id": item_id}

    def list_revisions(self, workspace_id: str, item_id: str) -> list[dict[str, Any]]:
        self._require_item(workspace_id, item_id, include_trashed=True)
        with self._lock:
            return self._fetchall(
                """
                SELECT * FROM document_vault_revisions
                WHERE workspace_id = ? AND item_id = ?
                ORDER BY revision DESC
                """,
                (workspace_id, item_id),
            )

    def restore_revision(
        self,
        workspace_id: str,
        item_id: str,
        revision: int,
        *,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._require_item(workspace_id, item_id, include_trashed=False)
            rev = self._fetchone(
                """
                SELECT * FROM document_vault_revisions
                WHERE workspace_id = ? AND item_id = ? AND revision = ?
                """,
                (workspace_id, item_id, int(revision)),
            )
            if not rev:
                raise VaultError("not_found", "revision not found")
        return self.update_item(
            workspace_id,
            item_id,
            storage_locator=rev.get("storage_locator"),
            byte_size=int(rev.get("byte_size") or 0),
            checksum=rev.get("checksum"),
            bump_revision=True,
            change_summary=f"restore revision {revision}",
            actor_id=actor_id,
        )

    def enqueue_job(
        self,
        workspace_id: str,
        kind: str,
        *,
        item_id: str | None = None,
        idempotency_key: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or f"{kind}:{item_id or ''}:{uuid.uuid4().hex[:8]}"
        with self._lock:
            existing = self._fetchone(
                """
                SELECT * FROM document_vault_jobs
                WHERE workspace_id = ? AND idempotency_key = ?
                """,
                (workspace_id, key),
            )
            if existing:
                return {**dict(existing), "idempotent": True}
            now = _utcnow()
            jid = str(uuid.uuid4())
            self._execute(
                """
                INSERT INTO document_vault_jobs (
                    id, workspace_id, kind, status, item_id, idempotency_key,
                    payload_json, result_json, error, created_at, updated_at
                ) VALUES (?, ?, ?, 'queued', ?, ?, ?, '{}', NULL, ?, ?)
                """,
                (jid, workspace_id, kind, item_id, key, _json_dumps(payload or {}), now, now),
            )
            self._commit()
            row = self._fetchone("SELECT * FROM document_vault_jobs WHERE id = ?", (jid,))
        return dict(row or {"id": jid})

    def list_jobs(self, workspace_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if status:
                return self._fetchall(
                    """
                    SELECT * FROM document_vault_jobs
                    WHERE workspace_id = ? AND status = ?
                    ORDER BY created_at DESC
                    """,
                    (workspace_id, status),
                )
            return self._fetchall(
                """
                SELECT * FROM document_vault_jobs
                WHERE workspace_id = ?
                ORDER BY created_at DESC
                """,
                (workspace_id,),
            )

    def upsert_source_mapping(
        self,
        workspace_id: str,
        *,
        source_store: str,
        source_id: str,
        item_id: str,
        idempotency_key: str,
        checksum: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            existing = self._fetchone(
                """
                SELECT * FROM document_vault_source_mappings
                WHERE workspace_id = ? AND idempotency_key = ?
                """,
                (workspace_id, idempotency_key),
            )
            if existing:
                return {**dict(existing), "idempotent": True}
            now = _utcnow()
            mid = str(uuid.uuid4())
            self._execute(
                """
                INSERT INTO document_vault_source_mappings (
                    id, workspace_id, source_store, source_id, item_id,
                    idempotency_key, checksum, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mid, workspace_id, source_store, source_id, item_id, idempotency_key, checksum, now),
            )
            self._commit()
            return {
                "id": mid,
                "workspace_id": workspace_id,
                "source_store": source_store,
                "source_id": source_id,
                "item_id": item_id,
                "idempotency_key": idempotency_key,
                "checksum": checksum,
                "idempotent": False,
            }

    def get_source_mapping(self, workspace_id: str, source_store: str, source_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._fetchone(
                """
                SELECT * FROM document_vault_source_mappings
                WHERE workspace_id = ? AND source_store = ? AND source_id = ?
                """,
                (workspace_id, source_store, source_id),
            )

    def _audit(
        self,
        workspace_id: str,
        *,
        item_id: str | None,
        action: str,
        actor_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        self._execute(
            """
            INSERT INTO document_vault_audit (
                id, workspace_id, item_id, action, actor_id, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), workspace_id, item_id, action, actor_id, _json_dumps(payload), _utcnow()),
        )

    def list_audit(self, workspace_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return self._fetchall(
                """
                SELECT * FROM document_vault_audit
                WHERE workspace_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (workspace_id, max(1, min(limit, 500))),
            )

    def upsert_provider_mapping(
        self,
        workspace_id: str,
        item_id: str,
        *,
        provider: str,
        provider_item_id: str,
        provider_revision: str | None = None,
        content_authority: str = "google",
        conflict_state: str | None = None,
        metadata: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
        with self._lock:
            existing = self._fetchone(
                """
                SELECT * FROM document_vault_provider_mappings
                WHERE workspace_id = ? AND provider = ? AND provider_item_id = ?
                """,
                (workspace_id, provider, provider_item_id),
            )
            now = _utcnow()
            if existing:
                self._execute(
                    """
                    UPDATE document_vault_provider_mappings
                    SET item_id = ?, provider_revision = ?, content_authority = ?,
                        last_synced_at = ?, conflict_state = ?, metadata_json = ?
                    WHERE id = ?
                    """,
                    (
                        item_id,
                        provider_revision,
                        content_authority,
                        now,
                        conflict_state,
                        _json_dumps(metadata or {}),
                        existing["id"],
                    ),
                )
                self._commit()
                row = self._fetchone(
                    "SELECT * FROM document_vault_provider_mappings WHERE id = ?",
                    (existing["id"],),
                )
            else:
                mid = str(uuid.uuid4())
                self._execute(
                    """
                    INSERT INTO document_vault_provider_mappings (
                        id, workspace_id, item_id, provider, provider_item_id,
                        provider_revision, content_authority, last_synced_at,
                        conflict_state, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mid,
                        workspace_id,
                        item_id,
                        provider,
                        provider_item_id,
                        provider_revision,
                        content_authority,
                        now,
                        conflict_state,
                        _json_dumps(metadata or {}),
                    ),
                )
                self._commit()
                row = self._fetchone(
                    "SELECT * FROM document_vault_provider_mappings WHERE id = ?",
                    (mid,),
                )
        out = dict(row or {})
        out["metadata"] = _json_loads(out.pop("metadata_json", "{}"))
        return out

    def get_provider_mapping_by_provider_id(
        self,
        workspace_id: str,
        provider: str,
        provider_item_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            row = self._fetchone(
                """
                SELECT * FROM document_vault_provider_mappings
                WHERE workspace_id = ? AND provider = ? AND provider_item_id = ?
                """,
                (workspace_id, provider, provider_item_id),
            )
        if not row:
            return None
        out = dict(row)
        out["metadata"] = _json_loads(out.pop("metadata_json", "{}"))
        return out

    def get_provider_mapping_for_item(
        self,
        workspace_id: str,
        item_id: str,
        provider: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            row = self._fetchone(
                """
                SELECT * FROM document_vault_provider_mappings
                WHERE workspace_id = ? AND item_id = ? AND provider = ?
                """,
                (workspace_id, item_id, provider),
            )
        if not row:
            return None
        out = dict(row)
        out["metadata"] = _json_loads(out.pop("metadata_json", "{}"))
        return out

    def list_conflicts(self, workspace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._fetchall(
                """
                SELECT * FROM document_vault_provider_mappings
                WHERE workspace_id = ? AND conflict_state IS NOT NULL AND conflict_state != ''
                ORDER BY last_synced_at DESC
                """,
                (workspace_id,),
            )
        out = []
        for row in rows:
            item = dict(row)
            item["metadata"] = _json_loads(item.pop("metadata_json", "{}"))
            out.append(item)
        return out

    def get_drive_connection(self, workspace_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._fetchone(
                "SELECT * FROM document_vault_drive_connections WHERE workspace_id = ?",
                (workspace_id,),
            )
        if not row:
            return None
        out = dict(row)
        out["connected"] = bool(out.get("connected"))
        out["shared_drives_enabled"] = bool(out.get("shared_drives_enabled"))
        out["scopes"] = _json_loads(out.pop("scopes_json", "[]"), default=[])
        # Never expose ciphertext via casual callers; service strips it.
        return out

    def upsert_drive_connection(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            existing = self._fetchone(
                "SELECT * FROM document_vault_drive_connections WHERE workspace_id = ?",
                (workspace_id,),
            )
            now = _utcnow()
            if not existing:
                self._execute(
                    """
                    INSERT INTO document_vault_drive_connections (
                        workspace_id, user_id, mode, root_folder_id, root_folder_name,
                        vault_root_item_id, page_token, channel_id, resource_id,
                        channel_expires_at, verification_token_hash, grant_ciphertext,
                        scopes_json, account_email, shared_drives_enabled, connected,
                        last_sync_at, last_error, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, NULL, ?)
                    """,
                    (
                        workspace_id,
                        str(fields.get("user_id") or "default"),
                        str(fields.get("mode") or "two_way"),
                        fields.get("root_folder_id"),
                        fields.get("root_folder_name"),
                        fields.get("vault_root_item_id"),
                        fields.get("page_token"),
                        fields.get("channel_id"),
                        fields.get("resource_id"),
                        fields.get("channel_expires_at"),
                        str(fields.get("verification_token_hash") or ""),
                        fields.get("grant_ciphertext"),
                        _json_dumps(fields.get("scopes") or []),
                        fields.get("account_email"),
                        now,
                    ),
                )
            self._commit()
        return self.update_drive_connection(workspace_id, **fields)

    def update_drive_connection(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        allowed = {
            "user_id",
            "mode",
            "root_folder_id",
            "root_folder_name",
            "vault_root_item_id",
            "page_token",
            "channel_id",
            "resource_id",
            "channel_expires_at",
            "verification_token_hash",
            "grant_ciphertext",
            "account_email",
            "last_sync_at",
            "last_error",
        }
        with self._lock:
            existing = self._fetchone(
                "SELECT * FROM document_vault_drive_connections WHERE workspace_id = ?",
                (workspace_id,),
            )
            if not existing:
                raise VaultError("not_found", "drive connection missing")
            sets: list[str] = []
            params: list[Any] = []
            for key, value in fields.items():
                if key == "scopes":
                    sets.append("scopes_json = ?")
                    params.append(_json_dumps(value or []))
                elif key == "connected":
                    sets.append("connected = ?")
                    params.append(1 if value else 0)
                elif key == "shared_drives_enabled":
                    # Shared Drives stay forced off until dedicated flags/tests exist.
                    sets.append("shared_drives_enabled = ?")
                    params.append(0)
                elif key in allowed:
                    sets.append(f"{key} = ?")
                    params.append(value)
            if sets:
                sets.append("updated_at = ?")
                params.append(_utcnow())
                params.append(workspace_id)
                self._execute(
                    f"UPDATE document_vault_drive_connections SET {', '.join(sets)} WHERE workspace_id = ?",
                    tuple(params),
                )
                self._commit()
        return self.get_drive_connection(workspace_id) or {}

    def delete_drive_connection(self, workspace_id: str) -> None:
        with self._lock:
            self._execute(
                "DELETE FROM document_vault_drive_connections WHERE workspace_id = ?",
                (workspace_id,),
            )
            self._execute(
                "DELETE FROM document_vault_drive_notifications WHERE workspace_id = ?",
                (workspace_id,),
            )
            self._commit()

    def seen_drive_notification(self, workspace_id: str, notification_id: str) -> bool:
        with self._lock:
            row = self._fetchone(
                """
                SELECT id FROM document_vault_drive_notifications
                WHERE workspace_id = ? AND notification_id = ?
                """,
                (workspace_id, notification_id),
            )
        return row is not None

    def record_drive_notification(self, workspace_id: str, notification_id: str) -> None:
        with self._lock:
            self._execute(
                """
                INSERT OR IGNORE INTO document_vault_drive_notifications (
                    id, workspace_id, notification_id, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), workspace_id, notification_id, _utcnow()),
            )
            self._commit()

    # ── Channel bindings / events / delivery (Prompt 651) ───────────

    def get_channel_binding(self, platform: str, channel_user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._fetchone(
                """
                SELECT * FROM document_vault_channel_bindings
                WHERE platform = ? AND channel_user_id = ?
                """,
                (platform, channel_user_id),
            )
        if not row:
            return None
        out = dict(row)
        out["grants"] = _json_loads(out.get("grants_json"), [])
        out["metadata"] = _json_loads(out.get("metadata_json"), {})
        return out

    def upsert_channel_binding(
        self,
        *,
        workspace_id: str,
        platform: str,
        channel_user_id: str,
        actor_id: str,
        audience: str = "private",
        grants: list[str] | None = None,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _utcnow()
        with self._lock:
            existing = self._fetchone(
                """
                SELECT * FROM document_vault_channel_bindings
                WHERE platform = ? AND channel_user_id = ?
                """,
                (platform, channel_user_id),
            )
            if existing:
                self._execute(
                    """
                    UPDATE document_vault_channel_bindings SET
                        workspace_id = ?, actor_id = ?, status = ?, audience = ?,
                        grants_json = ?, metadata_json = ?, updated_at = ?
                    WHERE platform = ? AND channel_user_id = ?
                    """,
                    (
                        workspace_id,
                        actor_id,
                        status,
                        audience,
                        _json_dumps(grants or []),
                        _json_dumps(metadata or {}),
                        now,
                        platform,
                        channel_user_id,
                    ),
                )
            else:
                self._execute(
                    """
                    INSERT INTO document_vault_channel_bindings (
                        id, workspace_id, platform, channel_user_id, actor_id,
                        status, audience, grants_json, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        workspace_id,
                        platform,
                        channel_user_id,
                        actor_id,
                        status,
                        audience,
                        _json_dumps(grants or []),
                        _json_dumps(metadata or {}),
                        now,
                        now,
                    ),
                )
            self._commit()
        return self.get_channel_binding(platform, channel_user_id) or {}

    def set_channel_binding_status(
        self,
        platform: str,
        channel_user_id: str,
        *,
        status: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            self._execute(
                """
                UPDATE document_vault_channel_bindings
                SET status = ?, updated_at = ?
                WHERE platform = ? AND channel_user_id = ?
                """,
                (status, _utcnow(), platform, channel_user_id),
            )
            self._commit()
        return self.get_channel_binding(platform, channel_user_id)

    def get_channel_event(
        self,
        workspace_id: str,
        platform: str,
        event_id: str,
        *,
        action: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            row = self._fetchone(
                """
                SELECT * FROM document_vault_channel_events
                WHERE workspace_id = ? AND platform = ? AND event_id = ? AND action = ?
                """,
                (workspace_id, platform, event_id, action),
            )
        if not row:
            return None
        out = dict(row)
        out["result"] = _json_loads(out.get("result_json"), {})
        return out

    def record_channel_event(
        self,
        workspace_id: str,
        *,
        platform: str,
        event_id: str,
        action: str,
        result_item_id: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _utcnow()
        with self._lock:
            existing = self.get_channel_event(workspace_id, platform, event_id, action=action)
            if existing:
                return existing
            eid = str(uuid.uuid4())
            self._execute(
                """
                INSERT INTO document_vault_channel_events (
                    id, workspace_id, platform, event_id, action,
                    result_item_id, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    workspace_id,
                    platform,
                    event_id,
                    action,
                    result_item_id,
                    _json_dumps(result or {}),
                    now,
                ),
            )
            self._commit()
        return self.get_channel_event(workspace_id, platform, event_id, action=action) or {"id": eid}

    def create_delivery_token(
        self,
        workspace_id: str,
        *,
        item_id: str,
        token_hash: str,
        expires_at: str,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        tid = str(uuid.uuid4())
        now = _utcnow()
        with self._lock:
            self._execute(
                """
                INSERT INTO document_vault_delivery_tokens (
                    id, workspace_id, item_id, token_hash, expires_at, created_by, created_at, consumed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (tid, workspace_id, item_id, token_hash, expires_at, created_by, now),
            )
            self._commit()
        return {
            "id": tid,
            "workspace_id": workspace_id,
            "item_id": item_id,
            "expires_at": expires_at,
        }

    def consume_delivery_token(self, token_hash: str) -> dict[str, Any] | None:
        now = _utcnow()
        with self._lock:
            row = self._fetchone(
                """
                SELECT * FROM document_vault_delivery_tokens
                WHERE token_hash = ? AND consumed_at IS NULL AND expires_at >= ?
                """,
                (token_hash, now),
            )
            if not row:
                return None
            self._execute(
                "UPDATE document_vault_delivery_tokens SET consumed_at = ? WHERE id = ?",
                (now, row["id"]),
            )
            self._commit()
            out = dict(row)
            out["consumed_at"] = now
            return out


def _split_sql(script: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    for ch in script:
        if ch == "'":
            in_single = not in_single
            buf.append(ch)
            continue
        if ch == ";" and not in_single:
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def resolve_backend() -> str:
    raw = (os.environ.get("KEPRIX_DOCUMENT_VAULT_BACKEND") or "auto").strip().lower()
    if raw in {"sqlite", "postgres"}:
        return raw
    force = os.environ.get("KEPRIX_DOCUMENT_VAULT_FORCE_PG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if force or (os.environ.get("KEPRIX_DATABASE_URL") and "pytest" not in os.environ.get("PYTEST_CURRENT_TEST", "")):
        try:
            from keprix.crm.pg_compat import ping_postgres

            if ping_postgres():
                return "postgres"
        except Exception:
            pass
    return "sqlite"


def get_document_vault_store() -> DocumentVaultStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            backend = resolve_backend()
            try:
                _STORE = DocumentVaultStore(backend=backend)
            except Exception:
                _STORE = DocumentVaultStore(backend="sqlite")
        return _STORE

def reset_document_vault_store_for_tests(path: Path | str) -> DocumentVaultStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is not None:
            try:
                _STORE.close()
            except Exception:
                pass
        _STORE = DocumentVaultStore(path=path, backend="sqlite")
        return _STORE
