"""Outreach ops tables: control, lists, bookings, Soft Wall approvals (standalone UI)."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.outreach.store import _data_root, _row_to_dict, get_outreach_store


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


OPS_SCHEMA = """
CREATE TABLE IF NOT EXISTS outreach_control (
    workspace_id TEXT PRIMARY KEY,
    paused INTEGER NOT NULL DEFAULT 0,
    reason TEXT,
    updated_by TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_lists (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    tags TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_list_members (
    workspace_id TEXT NOT NULL DEFAULT '',
    list_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    PRIMARY KEY (list_id, lead_id)
);

CREATE TABLE IF NOT EXISTS outreach_bookings (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    notes TEXT,
    attendee_name TEXT,
    attendee_email TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_approvals (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    message_id TEXT,
    enrollment_id TEXT,
    lead_id TEXT,
    recipient TEXT NOT NULL,
    subject TEXT,
    draft_body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    campaign_id TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS ix_outreach_lists_ws ON outreach_lists(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_bookings_ws ON outreach_bookings(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_approvals_ws ON outreach_approvals(workspace_id, status);
"""


def ensure_ops_workspace_columns(conn) -> None:
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(outreach_list_members)").fetchall()}
    if "workspace_id" not in cols:
        conn.execute(
            "ALTER TABLE outreach_list_members ADD COLUMN workspace_id TEXT NOT NULL DEFAULT ''"
        )
    conn.execute(
        """
        UPDATE outreach_list_members
        SET workspace_id = COALESCE(
            (SELECT l.workspace_id FROM outreach_lists l WHERE l.id = outreach_list_members.list_id),
            workspace_id,
            ''
        )
        WHERE COALESCE(workspace_id, '') = ''
        """
    )
    conn.commit()


class OutreachOpsStore:
    def __init__(self, path: Path | None = None) -> None:
        from keprix.crm.durable import resolve_crm_backend

        self._lock = threading.RLock()
        if path is not None:
            self._backend = "sqlite"
            self._path = Path(path)
        else:
            self._backend = resolve_crm_backend()
            self._path = _data_root() / "outreach.sqlite"

        if self._backend == "postgres":
            from keprix.crm.pg_compat import connect_crm_pg
            from keprix.outreach.schema_pg import ensure_outreach_pg_schema

            self._path = None
            self._conn = connect_crm_pg()
            ensure_outreach_pg_schema(self._conn)
        else:
            assert self._path is not None
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(OPS_SCHEMA)
            self._conn.commit()
            try:
                ensure_ops_workspace_columns(self._conn)
            except Exception:
                pass
            self._ensure_message_columns()

    @property
    def backend(self) -> str:
        return self._backend

    def _ensure_message_columns(self) -> None:
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(outreach_messages)").fetchall()}
        with self._lock:
            if "approval_status" not in cols:
                self._conn.execute(
                    "ALTER TABLE outreach_messages ADD COLUMN approval_status TEXT DEFAULT 'none'"
                )
            if "approval_id" not in cols:
                self._conn.execute("ALTER TABLE outreach_messages ADD COLUMN approval_id TEXT")
            if "workspace_id" not in cols:
                self._conn.execute(
                    "ALTER TABLE outreach_messages ADD COLUMN workspace_id TEXT NOT NULL DEFAULT ''"
                )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        return _row_to_dict(self._conn.execute(sql, params).fetchone())

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        return [d for r in self._conn.execute(sql, params).fetchall() if (d := _row_to_dict(r))]

    # Control
    def get_control(self, workspace_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM outreach_control WHERE workspace_id = ?", (workspace_id,))
        if not row:
            return {
                "workspace_id": workspace_id,
                "paused": False,
                "reason": None,
                "updated_by": None,
                "updated_at": _utcnow(),
            }
        return row

    def set_control(
        self,
        workspace_id: str,
        *,
        paused: bool,
        reason: str | None = None,
        updated_by: str | None = None,
    ) -> dict[str, Any]:
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_control (workspace_id, paused, reason, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id) DO UPDATE SET
                    paused = excluded.paused,
                    reason = excluded.reason,
                    updated_by = excluded.updated_by,
                    updated_at = excluded.updated_at
                """,
                (workspace_id, 1 if paused else 0, reason, updated_by, now),
            )
            self._conn.commit()
        return self.get_control(workspace_id)

    # Lists
    def list_lists(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM outreach_lists WHERE workspace_id = ? ORDER BY updated_at DESC",
            (workspace_id,),
        )
        for row in rows:
            members = self._fetchall(
                "SELECT lead_id FROM outreach_list_members WHERE list_id = ?",
                (row["id"],),
            )
            row["lead_ids"] = [m["lead_id"] for m in members]
            if isinstance(row.get("tags"), str):
                try:
                    row["tags"] = json.loads(row["tags"] or "[]")
                except json.JSONDecodeError:
                    row["tags"] = []
        return rows

    def create_list(self, workspace_id: str, name: str, **fields: Any) -> dict[str, Any]:
        now = _utcnow()
        list_id = str(uuid.uuid4())
        tags = fields.get("tags") or []
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_lists (id, workspace_id, name, description, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    list_id,
                    workspace_id,
                    name,
                    fields.get("description"),
                    json.dumps(tags),
                    now,
                    now,
                ),
            )
            for lead_id in fields.get("lead_ids") or []:
                self._conn.execute(
                    "INSERT OR IGNORE INTO outreach_list_members (workspace_id, list_id, lead_id) VALUES (?, ?, ?)",
                    (workspace_id, list_id, lead_id),
                )
            self._conn.commit()
        return next(x for x in self.list_lists(workspace_id) if x["id"] == list_id)

    def update_list(self, workspace_id: str, list_id: str, **fields: Any) -> dict[str, Any] | None:
        existing = self._fetchone(
            "SELECT * FROM outreach_lists WHERE id = ? AND workspace_id = ?",
            (list_id, workspace_id),
        )
        if not existing:
            return None
        name = fields.get("name", existing["name"])
        description = fields.get("description", existing.get("description"))
        tags = fields.get("tags")
        if tags is None:
            tags = existing.get("tags") or []
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags or "[]")
                except json.JSONDecodeError:
                    tags = []
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                UPDATE outreach_lists SET name = ?, description = ?, tags = ?, updated_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (name, description, json.dumps(tags), now, list_id, workspace_id),
            )
            if "lead_ids" in fields:
                self._conn.execute("DELETE FROM outreach_list_members WHERE list_id = ?", (list_id,))
                for lead_id in fields.get("lead_ids") or []:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO outreach_list_members (workspace_id, list_id, lead_id) VALUES (?, ?, ?)",
                        (workspace_id, list_id, lead_id),
                    )
            self._conn.commit()
        return next((x for x in self.list_lists(workspace_id) if x["id"] == list_id), None)

    def add_list_members(self, workspace_id: str, list_id: str, lead_ids: list[str]) -> dict[str, Any] | None:
        existing = self._fetchone(
            "SELECT id FROM outreach_lists WHERE id = ? AND workspace_id = ?",
            (list_id, workspace_id),
        )
        if not existing:
            return None
        with self._lock:
            for lead_id in lead_ids:
                self._conn.execute(
                    "INSERT OR IGNORE INTO outreach_list_members (workspace_id, list_id, lead_id) VALUES (?, ?, ?)",
                    (workspace_id, list_id, lead_id),
                )
            self._conn.execute(
                "UPDATE outreach_lists SET updated_at = ? WHERE id = ?",
                (_utcnow(), list_id),
            )
            self._conn.commit()
        return next((x for x in self.list_lists(workspace_id) if x["id"] == list_id), None)

    # Bookings
    def list_bookings(self, workspace_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM outreach_bookings WHERE workspace_id = ? ORDER BY starts_at ASC",
            (workspace_id,),
        )

    def create_booking(self, workspace_id: str, lead_id: str, starts_at: str, **fields: Any) -> dict[str, Any]:
        now = _utcnow()
        booking_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_bookings (
                    id, workspace_id, lead_id, starts_at, ends_at, status, notes,
                    attendee_name, attendee_email, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_id,
                    workspace_id,
                    lead_id,
                    starts_at,
                    fields.get("ends_at"),
                    fields.get("status") or "scheduled",
                    fields.get("notes"),
                    fields.get("attendee_name"),
                    fields.get("attendee_email"),
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return self._fetchone("SELECT * FROM outreach_bookings WHERE id = ?", (booking_id,))  # type: ignore[return-value]

    def update_booking_status(self, workspace_id: str, booking_id: str, status: str) -> dict[str, Any] | None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE outreach_bookings SET status = ?, updated_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (status, _utcnow(), booking_id, workspace_id),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM outreach_bookings WHERE id = ? AND workspace_id = ?",
            (booking_id, workspace_id),
        )

    # Soft Wall approvals
    def create_approval(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        approval_id = str(uuid.uuid4())
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_approvals (
                    id, workspace_id, message_id, enrollment_id, lead_id, recipient,
                    subject, draft_body, status, campaign_id, created_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, NULL)
                """,
                (
                    approval_id,
                    workspace_id,
                    fields.get("message_id"),
                    fields.get("enrollment_id"),
                    fields.get("lead_id"),
                    fields["recipient"],
                    fields.get("subject"),
                    fields.get("draft_body") or "",
                    fields.get("campaign_id"),
                    now,
                ),
            )
            if fields.get("message_id"):
                self._conn.execute(
                    """
                    UPDATE outreach_messages
                    SET approval_status = 'pending', approval_id = ?
                    WHERE id = ?
                    """,
                    (approval_id, fields["message_id"]),
                )
            self._conn.commit()
        return self._fetchone("SELECT * FROM outreach_approvals WHERE id = ?", (approval_id,))  # type: ignore[return-value]

    def list_approvals(self, workspace_id: str, status: str = "pending") -> list[dict[str, Any]]:
        if status:
            return self._fetchall(
                """
                SELECT * FROM outreach_approvals
                WHERE workspace_id = ? AND status = ?
                ORDER BY created_at DESC
                """,
                (workspace_id, status),
            )
        return self._fetchall(
            "SELECT * FROM outreach_approvals WHERE workspace_id = ? ORDER BY created_at DESC",
            (workspace_id,),
        )

    def resolve_approval(self, workspace_id: str, approval_id: str, status: str) -> dict[str, Any] | None:
        row = self._fetchone(
            "SELECT * FROM outreach_approvals WHERE id = ? AND workspace_id = ?",
            (approval_id, workspace_id),
        )
        if not row:
            return None
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                UPDATE outreach_approvals SET status = ?, resolved_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (status, now, approval_id, workspace_id),
            )
            if row.get("message_id"):
                sent_at = now if status == "approved" else None
                approval_status = "approved" if status == "approved" else "rejected"
                self._conn.execute(
                    """
                    UPDATE outreach_messages
                    SET approval_status = ?, sent_at = COALESCE(?, sent_at)
                    WHERE id = ?
                    """,
                    (approval_status, sent_at, row["message_id"]),
                )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM outreach_approvals WHERE id = ?",
            (approval_id,),
        )


_ops: OutreachOpsStore | None = None
_ops_lock = threading.Lock()


def get_outreach_ops_store(path: Path | None = None) -> OutreachOpsStore:
    global _ops
    if path is not None:
        return OutreachOpsStore(path=path)
    with _ops_lock:
        if _ops is None:
            main = get_outreach_store()
            if getattr(main, "backend", "sqlite") == "postgres":
                _ops = OutreachOpsStore()
            else:
                _ops = OutreachOpsStore(path=main._path)
        return _ops


def reset_outreach_ops_store_for_tests(path: Path | None = None) -> OutreachOpsStore:
    global _ops
    with _ops_lock:
        if _ops is not None:
            try:
                _ops.close()
            except Exception:
                pass
        _ops = OutreachOpsStore(path=path) if path else OutreachOpsStore()
        return _ops
