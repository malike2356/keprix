"""SQLite / Postgres outreach store (TEXT ids). Schema mirrors schema_pg."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _data_root() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "outreach"
    except Exception:
        root = Path.home() / ".keprix" / "outreach"
    root.mkdir(parents=True, exist_ok=True)
    return root


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS outreach_campaigns (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    source_type TEXT,
    daily_cap INTEGER DEFAULT 50,
    timezone TEXT DEFAULT 'Europe/London',
    business_hours_only INTEGER DEFAULT 1,
    warmup_days INTEGER DEFAULT 3,
    require_approval INTEGER DEFAULT 0,
    default_sequence_id TEXT,
    default_booking_link TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_sequences (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    channel_default TEXT DEFAULT 'email',
    stop_on_reply INTEGER DEFAULT 1,
    stop_on_booking INTEGER DEFAULT 1,
    stop_on_unsubscribe INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_sequence_steps (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL DEFAULT '',
    sequence_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    channel TEXT NOT NULL DEFAULT 'email',
    subject TEXT,
    body TEXT NOT NULL,
    cta TEXT,
    link TEXT,
    delay_hours INTEGER NOT NULL DEFAULT 24,
    UNIQUE(sequence_id, step_order)
);

CREATE TABLE IF NOT EXISTS outreach_leads (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    campaign_id TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    first_name TEXT,
    last_name TEXT,
    email TEXT NOT NULL,
    company TEXT,
    phone TEXT,
    source TEXT DEFAULT 'manual',
    source_url TEXT,
    tags TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_enrollments (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL DEFAULT '',
    lead_id TEXT NOT NULL,
    sequence_id TEXT NOT NULL,
    current_step INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    locked_until TEXT,
    locked_by TEXT,
    attempt_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_claimed_at TEXT,
    dead_letter_at TEXT,
    correlation_id TEXT
);

CREATE TABLE IF NOT EXISTS outreach_messages (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL DEFAULT '',
    enrollment_id TEXT NOT NULL,
    step_id TEXT,
    step_order INTEGER,
    channel TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    sent_at TEXT,
    delivered_at TEXT,
    opened_at TEXT,
    clicked_at TEXT,
    bounced INTEGER DEFAULT 0,
    approval_status TEXT DEFAULT 'none',
    approval_id TEXT,
    idempotency_key TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_scheduler_heartbeats (
    workspace_id TEXT NOT NULL DEFAULT '',
    worker_id TEXT NOT NULL,
    last_beat_at TEXT NOT NULL,
    queue_depth INTEGER DEFAULT 0,
    metadata_json TEXT,
    PRIMARY KEY (workspace_id, worker_id)
);

CREATE TABLE IF NOT EXISTS outreach_replies (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL DEFAULT '',
    lead_id TEXT,
    message_id TEXT,
    from_address TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    classification TEXT,
    confidence REAL,
    resolved INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_outreach_campaigns_workspace ON outreach_campaigns(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_sequences_workspace ON outreach_sequences(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_leads_workspace ON outreach_leads(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_leads_email ON outreach_leads(workspace_id, email);
CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_due ON outreach_enrollments(status, next_run_at);
CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_lease ON outreach_enrollments(status, locked_until);
CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_ws ON outreach_enrollments(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_messages_ws ON outreach_messages(workspace_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_outreach_messages_idem
    ON outreach_messages(workspace_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL AND idempotency_key != '';
CREATE INDEX IF NOT EXISTS ix_outreach_replies_ws ON outreach_replies(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_steps_ws ON outreach_sequence_steps(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_scheduler_hb_ws ON outreach_scheduler_heartbeats(workspace_id);
"""


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    if "tags" in data and isinstance(data["tags"], str):
        try:
            data["tags"] = json.loads(data["tags"] or "[]")
        except json.JSONDecodeError:
            data["tags"] = []
    for key in (
        "business_hours_only",
        "require_approval",
        "stop_on_reply",
        "stop_on_booking",
        "stop_on_unsubscribe",
        "bounced",
        "resolved",
    ):
        if key in data and data[key] is not None:
            data[key] = bool(data[key])
    return data


def ensure_outreach_workspace_columns(conn) -> None:
    """ADD workspace_id (and backfill) on child tables for older SQLite files."""

    def _cols(table: str) -> set[str]:
        return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    alters = (
        ("outreach_sequence_steps", "workspace_id TEXT NOT NULL DEFAULT ''"),
        ("outreach_enrollments", "workspace_id TEXT NOT NULL DEFAULT ''"),
        ("outreach_messages", "workspace_id TEXT NOT NULL DEFAULT ''"),
        ("outreach_replies", "workspace_id TEXT NOT NULL DEFAULT ''"),
    )
    for table, ddl in alters:
        cols = _cols(table)
        col_name = ddl.split()[0]
        if col_name not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    conn.execute(
        """
        UPDATE outreach_sequence_steps
        SET workspace_id = COALESCE(
            (SELECT s.workspace_id FROM outreach_sequences s WHERE s.id = outreach_sequence_steps.sequence_id),
            workspace_id,
            ''
        )
        WHERE COALESCE(workspace_id, '') = ''
        """
    )
    conn.execute(
        """
        UPDATE outreach_enrollments
        SET workspace_id = COALESCE(
            (SELECT l.workspace_id FROM outreach_leads l WHERE l.id = outreach_enrollments.lead_id),
            workspace_id,
            ''
        )
        WHERE COALESCE(workspace_id, '') = ''
        """
    )
    conn.execute(
        """
        UPDATE outreach_messages
        SET workspace_id = COALESCE(
            (SELECT e.workspace_id FROM outreach_enrollments e WHERE e.id = outreach_messages.enrollment_id),
            workspace_id,
            ''
        )
        WHERE COALESCE(workspace_id, '') = ''
        """
    )
    conn.execute(
        """
        UPDATE outreach_replies
        SET workspace_id = COALESCE(
            (SELECT l.workspace_id FROM outreach_leads l WHERE l.id = outreach_replies.lead_id),
            workspace_id,
            ''
        )
        WHERE COALESCE(workspace_id, '') = ''
        """
    )
    conn.commit()


def ensure_scheduler_columns(conn) -> None:
    """Additive scheduler / Soft Wall columns + indexes for older outreach DBs."""

    def _cols(table: str) -> set[str]:
        # Prefer information_schema on Postgres; PRAGMA via pg_compat also works.
        try:
            rows = conn.execute(
                """
                SELECT column_name AS name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = ?
                """,
                (table,),
            ).fetchall()
            if rows:
                names: set[str] = set()
                for r in rows:
                    if hasattr(r, "keys"):
                        names.add(str(r["name"] if "name" in r.keys() else r[0]))
                    else:
                        names.add(str(r[0]))
                return names
        except Exception:
            pass
        try:
            return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        except Exception:
            return set()

    enrollment_alters = (
        ("locked_until", "TEXT"),
        ("locked_by", "TEXT"),
        ("attempt_count", "INTEGER DEFAULT 0"),
        ("last_error", "TEXT"),
        ("last_claimed_at", "TEXT"),
        ("dead_letter_at", "TEXT"),
        ("correlation_id", "TEXT"),
    )
    cols = _cols("outreach_enrollments")
    for name, ddl in enrollment_alters:
        if name not in cols:
            try:
                conn.execute(f"ALTER TABLE outreach_enrollments ADD COLUMN {name} {ddl}")
            except Exception:
                # Concurrent / already-added race
                pass

    message_alters = (
        ("idempotency_key", "TEXT"),
        ("step_order", "INTEGER"),
        ("enrollment_id", "TEXT"),
        ("approval_status", "TEXT DEFAULT 'none'"),
        ("approval_id", "TEXT"),
    )
    msg_cols = _cols("outreach_messages")
    for name, ddl in message_alters:
        if name not in msg_cols:
            try:
                conn.execute(f"ALTER TABLE outreach_messages ADD COLUMN {name} {ddl}")
            except Exception:
                pass

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outreach_scheduler_heartbeats (
            workspace_id TEXT NOT NULL DEFAULT '',
            worker_id TEXT NOT NULL,
            last_beat_at TEXT NOT NULL,
            queue_depth INTEGER DEFAULT 0,
            metadata_json TEXT,
            PRIMARY KEY (workspace_id, worker_id)
        )
        """
    )
    # Indexes after columns exist (never in CREATE TABLE scripts alone for upgrades).
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_due ON outreach_enrollments(status, next_run_at)"
        )
    except Exception:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_lease ON outreach_enrollments(status, locked_until)"
        )
    except Exception:
        pass
    try:
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_outreach_messages_idem
            ON outreach_messages(workspace_id, idempotency_key)
            WHERE idempotency_key IS NOT NULL AND idempotency_key != ''
            """
        )
    except Exception:
        try:
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_outreach_messages_idem_pg
                ON outreach_messages(workspace_id, idempotency_key)
                """
            )
        except Exception:
            pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_outreach_scheduler_hb_ws ON outreach_scheduler_heartbeats(workspace_id)"
        )
    except Exception:
        pass
    try:
        conn.commit()
    except Exception:
        pass


class OutreachStore:
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
            try:
                ensure_scheduler_columns(self._conn)
            except Exception:
                pass
        else:
            assert self._path is not None
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.executescript(SQLITE_SCHEMA)
            self._conn.commit()
            try:
                ensure_outreach_workspace_columns(self._conn)
            except Exception:
                pass
            try:
                ensure_scheduler_columns(self._conn)
            except Exception:
                pass

    @property
    def backend(self) -> str:
        return self._backend

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        cur = self._conn.execute(sql, params)
        return _row_to_dict(cur.fetchone())

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        cur = self._conn.execute(sql, params)
        return [d for r in cur.fetchall() if (d := _row_to_dict(r))]

    def _require_workspace(self, workspace_id: str) -> str:
        ws = str(workspace_id or "").strip()
        if not ws:
            raise ValueError("workspace_id is required")
        return ws

    # ── Campaigns ──────────────────────────────────────────────
    def create_campaign(self, workspace_id: str, name: str, **fields: Any) -> dict[str, Any]:
        now = _utcnow()
        row_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_campaigns (
                    id, workspace_id, name, status, source_type, daily_cap, timezone,
                    business_hours_only, warmup_days, require_approval, default_sequence_id,
                    default_booking_link, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    workspace_id,
                    name,
                    fields.get("status") or "draft",
                    fields.get("source_type"),
                    int(fields.get("daily_cap") or 50),
                    fields.get("timezone") or "Europe/London",
                    1 if fields.get("business_hours_only", True) else 0,
                    int(fields.get("warmup_days") or 3),
                    1 if fields.get("require_approval") else 0,
                    fields.get("default_sequence_id"),
                    fields.get("default_booking_link"),
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return self.get_campaign(workspace_id, row_id)  # type: ignore[return-value]

    def get_campaign(self, workspace_id: str, campaign_id: str) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM outreach_campaigns WHERE id = ? AND workspace_id = ?",
            (campaign_id, workspace_id),
        )

    def list_campaigns(self, workspace_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM outreach_campaigns WHERE workspace_id = ? ORDER BY created_at DESC",
            (workspace_id,),
        )

    def update_campaign(self, workspace_id: str, campaign_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {
            "name",
            "status",
            "source_type",
            "daily_cap",
            "timezone",
            "business_hours_only",
            "warmup_days",
            "require_approval",
            "default_sequence_id",
            "default_booking_link",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_campaign(workspace_id, campaign_id)
        for bool_key in ("business_hours_only", "require_approval"):
            if bool_key in updates:
                updates[bool_key] = 1 if updates[bool_key] else 0
        updates["updated_at"] = _utcnow()
        cols = ", ".join(f"{k} = ?" for k in updates)
        with self._lock:
            self._conn.execute(
                f"UPDATE outreach_campaigns SET {cols} WHERE id = ? AND workspace_id = ?",
                (*updates.values(), campaign_id, workspace_id),
            )
            self._conn.commit()
        return self.get_campaign(workspace_id, campaign_id)

    # ── Sequences ──────────────────────────────────────────────
    def create_sequence(
        self,
        workspace_id: str,
        name: str,
        steps: list[dict[str, Any]] | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        now = _utcnow()
        seq_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_sequences (
                    id, workspace_id, name, channel_default, stop_on_reply,
                    stop_on_booking, stop_on_unsubscribe, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    seq_id,
                    workspace_id,
                    name,
                    fields.get("channel_default") or "email",
                    1 if fields.get("stop_on_reply", True) else 0,
                    1 if fields.get("stop_on_booking", True) else 0,
                    1 if fields.get("stop_on_unsubscribe", True) else 0,
                    now,
                ),
            )
            for idx, step in enumerate(steps or [], start=1):
                self._conn.execute(
                    """
                    INSERT INTO outreach_sequence_steps (
                        id, workspace_id, sequence_id, step_order, channel, subject, body, cta, link, delay_hours
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        workspace_id,
                        seq_id,
                        int(step.get("step_order") or idx),
                        step.get("channel") or "email",
                        step.get("subject"),
                        str(step.get("body") or ""),
                        step.get("cta"),
                        step.get("link"),
                        int(step.get("delay_hours") if step.get("delay_hours") is not None else 24),
                    ),
                )
            self._conn.commit()
        return self.get_sequence(workspace_id, seq_id)  # type: ignore[return-value]

    def get_sequence(self, workspace_id: str, sequence_id: str) -> dict[str, Any] | None:
        seq = self._fetchone(
            "SELECT * FROM outreach_sequences WHERE id = ? AND workspace_id = ?",
            (sequence_id, workspace_id),
        )
        if not seq:
            return None
        seq["steps"] = self._fetchall(
            "SELECT * FROM outreach_sequence_steps WHERE sequence_id = ? AND workspace_id = ? ORDER BY step_order ASC",
            (sequence_id, workspace_id),
        )
        return seq

    def list_sequences(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM outreach_sequences WHERE workspace_id = ? ORDER BY created_at DESC",
            (workspace_id,),
        )
        for row in rows:
            row["steps"] = self.list_steps(str(row["id"]))
        return rows

    def list_steps(self, sequence_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM outreach_sequence_steps WHERE sequence_id = ? ORDER BY step_order ASC",
            (sequence_id,),
        )

    # ── Leads ──────────────────────────────────────────────────
    def add_leads(
        self,
        workspace_id: str,
        leads: list[dict[str, Any]],
        campaign_id: str | None = None,
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        now = _utcnow()
        with self._lock:
            for lead in leads:
                email = str(lead.get("email") or "").strip().lower()
                if not email:
                    continue
                existing = self._fetchone(
                    "SELECT * FROM outreach_leads WHERE workspace_id = ? AND lower(email) = ?",
                    (workspace_id, email),
                )
                if existing:
                    created.append(existing)
                    continue
                lead_id = str(uuid.uuid4())
                tags = lead.get("tags") or []
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                self._conn.execute(
                    """
                    INSERT INTO outreach_leads (
                        id, workspace_id, campaign_id, status, first_name, last_name, email,
                        company, phone, source, source_url, tags, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lead_id,
                        workspace_id,
                        campaign_id or lead.get("campaign_id"),
                        lead.get("status") or "new",
                        lead.get("first_name"),
                        lead.get("last_name"),
                        email,
                        lead.get("company"),
                        lead.get("phone"),
                        lead.get("source") or "manual",
                        lead.get("source_url"),
                        json.dumps(list(tags)),
                        lead.get("notes"),
                        now,
                        now,
                    ),
                )
                created.append(
                    self._fetchone("SELECT * FROM outreach_leads WHERE id = ?", (lead_id,))
                )
            self._conn.commit()
        return [c for c in created if c]

    def get_lead(self, workspace_id: str, lead_id: str) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM outreach_leads WHERE id = ? AND workspace_id = ?",
            (lead_id, workspace_id),
        )

    def find_lead_by_email(self, workspace_id: str, email: str) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM outreach_leads WHERE workspace_id = ? AND lower(email) = ?",
            (workspace_id, email.strip().lower()),
        )

    def update_lead_status(self, workspace_id: str, lead_id: str, status: str) -> dict[str, Any] | None:
        with self._lock:
            self._conn.execute(
                "UPDATE outreach_leads SET status = ?, updated_at = ? WHERE id = ? AND workspace_id = ?",
                (status, _utcnow(), lead_id, workspace_id),
            )
            self._conn.commit()
        return self.get_lead(workspace_id, lead_id)

    def pipeline_counts(self, workspace_id: str, campaign_id: str | None = None) -> dict[str, int]:
        sql = "SELECT status, COUNT(*) AS c FROM outreach_leads WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if campaign_id:
            sql += " AND campaign_id = ?"
            params.append(campaign_id)
        sql += " GROUP BY status"
        rows = self._fetchall(sql, tuple(params))
        return {str(r["status"]): int(r["c"]) for r in rows}

    def list_leads(
        self,
        workspace_id: str,
        *,
        campaign_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM outreach_leads WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if campaign_id:
            sql += " AND campaign_id = ?"
            params.append(campaign_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        return self._fetchall(sql, tuple(params))

    # ── Enrollments ────────────────────────────────────────────
    def enroll_lead(
        self,
        lead_id: str,
        sequence_id: str,
        *,
        workspace_id: str | None = None,
        next_run_at: str | None = None,
    ) -> dict[str, Any]:
        now = _utcnow()
        enrollment_id = str(uuid.uuid4())
        ws = workspace_id
        if not ws:
            lead = self._fetchone("SELECT workspace_id FROM outreach_leads WHERE id = ?", (lead_id,))
            ws = str((lead or {}).get("workspace_id") or "")
        ws = self._require_workspace(ws)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_enrollments (
                    id, workspace_id, lead_id, sequence_id, current_step, next_run_at, status, created_at
                ) VALUES (?, ?, ?, ?, 0, ?, 'active', ?)
                """,
                (enrollment_id, ws, lead_id, sequence_id, next_run_at or now, now),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM outreach_enrollments WHERE id = ? AND workspace_id = ?",
            (enrollment_id, ws),
        )  # type: ignore[return-value]

    def get_enrollment(
        self, enrollment_id: str, workspace_id: str | None = None
    ) -> dict[str, Any] | None:
        if workspace_id:
            return self._fetchone(
                "SELECT * FROM outreach_enrollments WHERE id = ? AND workspace_id = ?",
                (enrollment_id, workspace_id),
            )
        return self._fetchone("SELECT * FROM outreach_enrollments WHERE id = ?", (enrollment_id,))

    def list_due_enrollments(self, *, now_iso: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        now = now_iso or _utcnow()
        return self._fetchall(
            """
            SELECT e.* FROM outreach_enrollments e
            WHERE e.status = 'active' AND e.next_run_at IS NOT NULL AND e.next_run_at <= ?
              AND (e.locked_until IS NULL OR e.locked_until < ?)
            ORDER BY e.next_run_at ASC
            LIMIT ?
            """,
            (now, now, limit),
        )

    def update_enrollment(self, enrollment_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {
            "current_step",
            "next_run_at",
            "status",
            "locked_until",
            "locked_by",
            "attempt_count",
            "last_error",
            "last_claimed_at",
            "dead_letter_at",
            "correlation_id",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        existing = self.get_enrollment(enrollment_id)
        if not existing:
            return None
        if not updates:
            return existing
        ws = str(existing.get("workspace_id") or "")
        cols = ", ".join(f"{k} = ?" for k in updates)
        with self._lock:
            if ws:
                self._conn.execute(
                    f"UPDATE outreach_enrollments SET {cols} WHERE id = ? AND workspace_id = ?",
                    (*updates.values(), enrollment_id, ws),
                )
            else:
                self._conn.execute(
                    f"UPDATE outreach_enrollments SET {cols} WHERE id = ?",
                    (*updates.values(), enrollment_id),
                )
            self._conn.commit()
        return self.get_enrollment(enrollment_id, workspace_id=ws or None)

    def _parse_iso_dt(self, value: str) -> datetime:
        raw = value.replace("Z", "+00:00") if value.endswith("Z") else value
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def claim_due_enrollments(
        self,
        *,
        now_iso: str,
        limit: int,
        worker_id: str,
        lease_seconds: int = 60,
        workspace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Atomically claim due active enrollments with a short lease."""
        from datetime import timedelta

        now_dt = self._parse_iso_dt(now_iso)
        locked_until = (now_dt + timedelta(seconds=max(1, int(lease_seconds)))).replace(
            microsecond=0
        ).isoformat()
        claimed: list[dict[str, Any]] = []
        worker = str(worker_id or "worker").strip() or "worker"
        lim = max(1, int(limit))

        with self._lock:
            if self._backend == "postgres":
                try:
                    claimed = self._claim_due_postgres(
                        now_iso=now_iso,
                        locked_until=locked_until,
                        worker_id=worker,
                        limit=lim,
                        workspace_id=workspace_id,
                    )
                    if claimed is not None:
                        return claimed
                except Exception:
                    claimed = []

            sql = """
                SELECT e.* FROM outreach_enrollments e
                WHERE e.status = 'active'
                  AND e.next_run_at IS NOT NULL
                  AND e.next_run_at <= ?
                  AND (e.locked_until IS NULL OR e.locked_until < ?)
            """
            params: list[Any] = [now_iso, now_iso]
            if workspace_id:
                sql += " AND e.workspace_id = ?"
                params.append(workspace_id)
            sql += " ORDER BY e.next_run_at ASC LIMIT ?"
            params.append(lim)
            candidates = self._fetchall(sql, tuple(params))
            for row in candidates:
                cur = self._conn.execute(
                    """
                    UPDATE outreach_enrollments
                    SET locked_until = ?, locked_by = ?, last_claimed_at = ?
                    WHERE id = ?
                      AND status = 'active'
                      AND next_run_at IS NOT NULL
                      AND next_run_at <= ?
                      AND (locked_until IS NULL OR locked_until < ?)
                    """,
                    (locked_until, worker, now_iso, row["id"], now_iso, now_iso),
                )
                if int(getattr(cur, "rowcount", 0) or 0) > 0:
                    refreshed = self._fetchone(
                        "SELECT * FROM outreach_enrollments WHERE id = ?",
                        (row["id"],),
                    )
                    if refreshed:
                        claimed.append(refreshed)
            self._conn.commit()
        return claimed

    def _claim_due_postgres(
        self,
        *,
        now_iso: str,
        locked_until: str,
        worker_id: str,
        limit: int,
        workspace_id: str | None,
    ) -> list[dict[str, Any]] | None:
        """Prefer SKIP LOCKED claim; return None to fall back to CAS loop."""
        ws_filter = " AND workspace_id = %s" if workspace_id else ""
        params: list[Any] = [now_iso, now_iso]
        if workspace_id:
            params.append(workspace_id)
        params.extend([locked_until, worker_id, now_iso, limit])
        # pg_compat uses ? placeholders typically; try both styles.
        try:
            sql = f"""
                UPDATE outreach_enrollments
                SET locked_until = ?, locked_by = ?, last_claimed_at = ?
                WHERE id IN (
                    SELECT id FROM outreach_enrollments
                    WHERE status = 'active'
                      AND next_run_at IS NOT NULL
                      AND next_run_at <= ?
                      AND (locked_until IS NULL OR locked_until < ?)
                      {ws_filter.replace('%s', '?') if workspace_id else ''}
                    ORDER BY next_run_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT ?
                )
                RETURNING *
            """
            # Build params for UPDATE SET then subquery WHERE then LIMIT
            # Reorder: SET values first, then subquery filters, then limit
            if workspace_id:
                exec_params = (
                    locked_until,
                    worker_id,
                    now_iso,
                    now_iso,
                    now_iso,
                    workspace_id,
                    limit,
                )
            else:
                exec_params = (
                    locked_until,
                    worker_id,
                    now_iso,
                    now_iso,
                    now_iso,
                    limit,
                )
            cur = self._conn.execute(sql, exec_params)
            rows = cur.fetchall()
            self._conn.commit()
            out: list[dict[str, Any]] = []
            for r in rows:
                d = _row_to_dict(r) if not isinstance(r, dict) else r
                if d:
                    out.append(d)
            return out
        except Exception:
            return None

    def release_enrollment_lock(self, enrollment_id: str, worker_id: str | None = None) -> dict[str, Any] | None:
        existing = self.get_enrollment(enrollment_id)
        if not existing:
            return None
        with self._lock:
            if worker_id:
                self._conn.execute(
                    """
                    UPDATE outreach_enrollments
                    SET locked_until = NULL, locked_by = NULL
                    WHERE id = ? AND (locked_by IS NULL OR locked_by = ?)
                    """,
                    (enrollment_id, worker_id),
                )
            else:
                self._conn.execute(
                    """
                    UPDATE outreach_enrollments
                    SET locked_until = NULL, locked_by = NULL
                    WHERE id = ?
                    """,
                    (enrollment_id,),
                )
            self._conn.commit()
        return self.get_enrollment(enrollment_id)

    def reclaim_stale_enrollment_locks(self, *, now_iso: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                """
                UPDATE outreach_enrollments
                SET locked_until = NULL, locked_by = NULL
                WHERE locked_until IS NOT NULL AND locked_until < ?
                """,
                (now_iso,),
            )
            self._conn.commit()
            return int(getattr(cur, "rowcount", 0) or 0)

    def record_scheduler_heartbeat(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        queue_depth: int = 0,
        metadata: dict[str, Any] | None = None,
        now_iso: str | None = None,
    ) -> None:
        now = now_iso or _utcnow()
        ws = str(workspace_id or "")
        wid = str(worker_id or "worker")
        meta = json.dumps(metadata or {})
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_scheduler_heartbeats (
                    workspace_id, worker_id, last_beat_at, queue_depth, metadata_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id, worker_id) DO UPDATE SET
                    last_beat_at = excluded.last_beat_at,
                    queue_depth = excluded.queue_depth,
                    metadata_json = excluded.metadata_json
                """,
                (ws, wid, now, int(queue_depth), meta),
            )
            self._conn.commit()

    def get_scheduler_health(self, workspace_id: str | None = None) -> dict[str, Any]:
        now = _utcnow()
        ws_clause = " AND workspace_id = ?" if workspace_id else ""
        ws_params: tuple[Any, ...] = (workspace_id,) if workspace_id else ()

        due_row = self._fetchone(
            f"""
            SELECT COUNT(*) AS c FROM outreach_enrollments
            WHERE status = 'active'
              AND next_run_at IS NOT NULL
              AND next_run_at <= ?
              AND (locked_until IS NULL OR locked_until < ?)
              {ws_clause}
            """,
            (now, now, *ws_params),
        )
        awaiting = self._fetchone(
            f"SELECT COUNT(*) AS c FROM outreach_enrollments WHERE status = 'awaiting_approval'{ws_clause}",
            ws_params,
        )
        dead = self._fetchone(
            f"SELECT COUNT(*) AS c FROM outreach_enrollments WHERE status = 'dead_letter'{ws_clause}",
            ws_params,
        )
        retrying = self._fetchone(
            f"""
            SELECT COUNT(*) AS c FROM outreach_enrollments
            WHERE status = 'active' AND COALESCE(attempt_count, 0) > 0{ws_clause}
            """,
            ws_params,
        )
        oldest = self._fetchone(
            f"""
            SELECT next_run_at FROM outreach_enrollments
            WHERE status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= ?
              {ws_clause}
            ORDER BY next_run_at ASC LIMIT 1
            """,
            (now, *ws_params),
        )
        oldest_age = None
        if oldest and oldest.get("next_run_at"):
            try:
                due_at = self._parse_iso_dt(str(oldest["next_run_at"]))
                oldest_age = max(0, int((self._parse_iso_dt(now) - due_at).total_seconds()))
            except Exception:
                oldest_age = None

        hb_sql = "SELECT * FROM outreach_scheduler_heartbeats"
        hb_params: tuple[Any, ...] = ()
        if workspace_id:
            hb_sql += " WHERE workspace_id = ?"
            hb_params = (workspace_id,)
        hb_sql += " ORDER BY last_beat_at DESC LIMIT 5"
        heartbeats = self._fetchall(hb_sql, hb_params)
        latest = heartbeats[0] if heartbeats else None
        return {
            "workspace_id": workspace_id,
            "at": now,
            "queue_depth": int((due_row or {}).get("c") or 0),
            "awaiting_approval_count": int((awaiting or {}).get("c") or 0),
            "dead_letter_count": int((dead or {}).get("c") or 0),
            "retrying_count": int((retrying or {}).get("c") or 0),
            "oldest_due_age_seconds": oldest_age,
            "heartbeat": latest,
            "heartbeats": heartbeats,
        }

    def pause_enrollment(self, enrollment_id: str, *, reason: str | None = None) -> dict[str, Any] | None:
        return self.update_enrollment(
            enrollment_id,
            status="paused",
            next_run_at=None,
            locked_until=None,
            locked_by=None,
            last_error=reason,
        )

    def resume_enrollment(self, enrollment_id: str, *, next_run_at: str | None = None) -> dict[str, Any] | None:
        return self.update_enrollment(
            enrollment_id,
            status="active",
            next_run_at=next_run_at or _utcnow(),
            last_error=None,
            locked_until=None,
            locked_by=None,
        )

    def cancel_enrollment(self, enrollment_id: str, *, reason: str | None = None) -> dict[str, Any] | None:
        return self.update_enrollment(
            enrollment_id,
            status="cancelled",
            next_run_at=None,
            locked_until=None,
            locked_by=None,
            last_error=reason,
        )

    def retry_dead_letter(self, enrollment_id: str, *, next_run_at: str | None = None) -> dict[str, Any] | None:
        existing = self.get_enrollment(enrollment_id)
        if not existing or existing.get("status") != "dead_letter":
            return existing
        return self.update_enrollment(
            enrollment_id,
            status="active",
            next_run_at=next_run_at or _utcnow(),
            attempt_count=0,
            last_error=None,
            dead_letter_at=None,
            locked_until=None,
            locked_by=None,
        )

    def drain_enrollments(
        self,
        *,
        workspace_id: str | None = None,
        campaign_id: str | None = None,
    ) -> int:
        """Cancel all active enrollments for a workspace or campaign."""
        with self._lock:
            if campaign_id:
                cur = self._conn.execute(
                    """
                    UPDATE outreach_enrollments
                    SET status = 'cancelled', next_run_at = NULL, locked_until = NULL, locked_by = NULL
                    WHERE status = 'active'
                      AND lead_id IN (
                        SELECT id FROM outreach_leads
                        WHERE campaign_id = ?
                          AND (? IS NULL OR workspace_id = ?)
                      )
                    """,
                    (campaign_id, workspace_id, workspace_id),
                )
            elif workspace_id:
                cur = self._conn.execute(
                    """
                    UPDATE outreach_enrollments
                    SET status = 'cancelled', next_run_at = NULL, locked_until = NULL, locked_by = NULL
                    WHERE status = 'active' AND workspace_id = ?
                    """,
                    (workspace_id,),
                )
            else:
                return 0
            self._conn.commit()
            return int(getattr(cur, "rowcount", 0) or 0)

    def active_enrollments_for_lead(
        self, lead_id: str, *, workspace_id: str | None = None
    ) -> list[dict[str, Any]]:
        if workspace_id:
            return self._fetchall(
                """
                SELECT * FROM outreach_enrollments
                WHERE lead_id = ? AND workspace_id = ? AND status = 'active'
                """,
                (lead_id, workspace_id),
            )
        return self._fetchall(
            "SELECT * FROM outreach_enrollments WHERE lead_id = ? AND status = 'active'",
            (lead_id,),
        )

    # ── Messages / replies ─────────────────────────────────────
    def create_message(self, **fields: Any) -> dict[str, Any]:
        now = _utcnow()
        enrollment_id = fields["enrollment_id"]
        ws = fields.get("workspace_id")
        if not ws:
            enr = self._fetchone(
                "SELECT workspace_id FROM outreach_enrollments WHERE id = ?",
                (enrollment_id,),
            )
            ws = str((enr or {}).get("workspace_id") or "")
        ws = self._require_workspace(ws)
        idem = fields.get("idempotency_key")
        idem_key = str(idem).strip() if idem else None
        with self._lock:
            if idem_key:
                existing = self._fetchone(
                    """
                    SELECT * FROM outreach_messages
                    WHERE workspace_id = ? AND idempotency_key = ?
                    """,
                    (ws, idem_key),
                )
                if existing:
                    return existing
            msg_id = str(uuid.uuid4())
            try:
                self._conn.execute(
                    """
                    INSERT INTO outreach_messages (
                        id, workspace_id, enrollment_id, step_id, step_order, channel, subject, body,
                        sent_at, delivered_at, opened_at, clicked_at, bounced,
                        approval_status, approval_id, idempotency_key, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        msg_id,
                        ws,
                        enrollment_id,
                        fields.get("step_id"),
                        fields.get("step_order"),
                        fields.get("channel") or "email",
                        fields.get("subject"),
                        fields.get("body") or "",
                        fields.get("sent_at"),
                        fields.get("delivered_at"),
                        fields.get("opened_at"),
                        fields.get("clicked_at"),
                        1 if fields.get("bounced") else 0,
                        fields.get("approval_status") or "none",
                        fields.get("approval_id"),
                        idem_key,
                        now,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                if idem_key:
                    existing = self._fetchone(
                        """
                        SELECT * FROM outreach_messages
                        WHERE workspace_id = ? AND idempotency_key = ?
                        """,
                        (ws, idem_key),
                    )
                    if existing:
                        return existing
                raise
        return self._fetchone(
            "SELECT * FROM outreach_messages WHERE id = ? AND workspace_id = ?",
            (msg_id, ws),
        )  # type: ignore[return-value]

    def count_messages_for_enrollment_step(self, enrollment_id: str, step_order: int) -> int:
        row = self._fetchone(
            """
            SELECT COUNT(*) AS c FROM outreach_messages
            WHERE enrollment_id = ? AND step_order = ?
            """,
            (enrollment_id, step_order),
        )
        return int((row or {}).get("c") or 0)

    def count_messages_sent_today(self, campaign_id: str, day_prefix: str) -> int:
        row = self._fetchone(
            """
            SELECT COUNT(*) AS c FROM outreach_messages m
            JOIN outreach_enrollments e ON e.id = m.enrollment_id
            JOIN outreach_leads l ON l.id = e.lead_id
            WHERE l.campaign_id = ? AND m.sent_at IS NOT NULL AND m.sent_at LIKE ?
            """,
            (campaign_id, f"{day_prefix}%"),
        )
        return int((row or {}).get("c") or 0)

    def create_reply(self, **fields: Any) -> dict[str, Any]:
        reply_id = str(uuid.uuid4())
        now = _utcnow()
        lead_id = fields.get("lead_id")
        ws = fields.get("workspace_id")
        if not ws and lead_id:
            lead = self._fetchone(
                "SELECT workspace_id FROM outreach_leads WHERE id = ?",
                (lead_id,),
            )
            ws = str((lead or {}).get("workspace_id") or "")
        ws = self._require_workspace(ws)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_replies (
                    id, workspace_id, lead_id, message_id, from_address, subject, body,
                    classification, confidence, resolved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reply_id,
                    ws,
                    lead_id,
                    fields.get("message_id"),
                    fields["from_address"],
                    fields.get("subject"),
                    fields.get("body") or "",
                    fields.get("classification"),
                    fields.get("confidence"),
                    1 if fields.get("resolved") else 0,
                    now,
                ),
            )
            self._conn.commit()
        return self._fetchone(
            "SELECT * FROM outreach_replies WHERE id = ? AND workspace_id = ?",
            (reply_id, ws),
        )  # type: ignore[return-value]

    def campaign_stats(self, workspace_id: str, campaign_id: str) -> dict[str, Any]:
        campaign = self.get_campaign(workspace_id, campaign_id)
        if not campaign:
            return {"error": "campaign_not_found"}
        leads = self._fetchone(
            "SELECT COUNT(*) AS c FROM outreach_leads WHERE workspace_id = ? AND campaign_id = ?",
            (workspace_id, campaign_id),
        )
        messages = self._fetchone(
            """
            SELECT COUNT(*) AS c FROM outreach_messages m
            JOIN outreach_enrollments e ON e.id = m.enrollment_id
            JOIN outreach_leads l ON l.id = e.lead_id
            WHERE l.workspace_id = ? AND l.campaign_id = ? AND m.sent_at IS NOT NULL
            """,
            (workspace_id, campaign_id),
        )
        replies = self._fetchone(
            """
            SELECT COUNT(*) AS c FROM outreach_replies r
            JOIN outreach_leads l ON l.id = r.lead_id
            WHERE l.workspace_id = ? AND l.campaign_id = ?
            """,
            (workspace_id, campaign_id),
        )
        return {
            "campaign": campaign,
            "leads": int((leads or {}).get("c") or 0),
            "messages_sent": int((messages or {}).get("c") or 0),
            "replies": int((replies or {}).get("c") or 0),
            "pipeline": self.pipeline_counts(workspace_id, campaign_id),
        }

    def digest_summary(self, workspace_id: str, since_iso: str) -> dict[str, Any]:
        new_leads = self._fetchone(
            "SELECT COUNT(*) AS c FROM outreach_leads WHERE workspace_id = ? AND created_at >= ?",
            (workspace_id, since_iso),
        )
        replies = self._fetchone(
            """
            SELECT COUNT(*) AS c FROM outreach_replies r
            JOIN outreach_leads l ON l.id = r.lead_id
            WHERE l.workspace_id = ? AND r.created_at >= ?
            """,
            (workspace_id, since_iso),
        )
        bookings = self._fetchone(
            """
            SELECT COUNT(*) AS c FROM outreach_leads
            WHERE workspace_id = ? AND status = 'booking' AND updated_at >= ?
            """,
            (workspace_id, since_iso),
        )
        return {
            "workspace_id": workspace_id,
            "since": since_iso,
            "new_leads": int((new_leads or {}).get("c") or 0),
            "replies": int((replies or {}).get("c") or 0),
            "bookings": int((bookings or {}).get("c") or 0),
            "pipeline": self.pipeline_counts(workspace_id),
        }


_store: OutreachStore | None = None
_store_lock = threading.Lock()


def get_outreach_store(path: Path | None = None) -> OutreachStore:
    global _store
    if path is not None:
        return OutreachStore(path=path)
    with _store_lock:
        if _store is None:
            _store = OutreachStore()
        return _store


def reset_outreach_store_for_tests(path: Path | None = None) -> OutreachStore:
    global _store
    with _store_lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = OutreachStore(path=path) if path else OutreachStore()
        return _store
