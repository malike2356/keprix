"""SQLite-backed outreach store (K02). Schema mirrors Postgres tables."""

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
    lead_id TEXT NOT NULL,
    sequence_id TEXT NOT NULL,
    current_step INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_messages (
    id TEXT PRIMARY KEY,
    enrollment_id TEXT NOT NULL,
    step_id TEXT,
    channel TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    sent_at TEXT,
    delivered_at TEXT,
    opened_at TEXT,
    clicked_at TEXT,
    bounced INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_replies (
    id TEXT PRIMARY KEY,
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


class OutreachStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (_data_root() / "outreach.sqlite")
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SQLITE_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        cur = self._conn.execute(sql, params)
        return _row_to_dict(cur.fetchone())

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        cur = self._conn.execute(sql, params)
        return [d for r in cur.fetchall() if (d := _row_to_dict(r))]

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
                        id, sequence_id, step_order, channel, subject, body, cta, link, delay_hours
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
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
            "SELECT * FROM outreach_sequence_steps WHERE sequence_id = ? ORDER BY step_order ASC",
            (sequence_id,),
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
        next_run_at: str | None = None,
    ) -> dict[str, Any]:
        now = _utcnow()
        enrollment_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_enrollments (
                    id, lead_id, sequence_id, current_step, next_run_at, status, created_at
                ) VALUES (?, ?, ?, 0, ?, 'active', ?)
                """,
                (enrollment_id, lead_id, sequence_id, next_run_at or now, now),
            )
            self._conn.commit()
        return self._fetchone("SELECT * FROM outreach_enrollments WHERE id = ?", (enrollment_id,))  # type: ignore[return-value]

    def get_enrollment(self, enrollment_id: str) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM outreach_enrollments WHERE id = ?", (enrollment_id,))

    def list_due_enrollments(self, *, now_iso: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        now = now_iso or _utcnow()
        return self._fetchall(
            """
            SELECT e.* FROM outreach_enrollments e
            WHERE e.status = 'active' AND e.next_run_at IS NOT NULL AND e.next_run_at <= ?
            ORDER BY e.next_run_at ASC
            LIMIT ?
            """,
            (now, limit),
        )

    def update_enrollment(self, enrollment_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {"current_step", "next_run_at", "status"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_enrollment(enrollment_id)
        cols = ", ".join(f"{k} = ?" for k in updates)
        with self._lock:
            self._conn.execute(
                f"UPDATE outreach_enrollments SET {cols} WHERE id = ?",
                (*updates.values(), enrollment_id),
            )
            self._conn.commit()
        return self.get_enrollment(enrollment_id)

    def active_enrollments_for_lead(self, lead_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM outreach_enrollments WHERE lead_id = ? AND status = 'active'",
            (lead_id,),
        )

    # ── Messages / replies ─────────────────────────────────────
    def create_message(self, **fields: Any) -> dict[str, Any]:
        msg_id = str(uuid.uuid4())
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_messages (
                    id, enrollment_id, step_id, channel, subject, body,
                    sent_at, delivered_at, opened_at, clicked_at, bounced, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_id,
                    fields["enrollment_id"],
                    fields.get("step_id"),
                    fields.get("channel") or "email",
                    fields.get("subject"),
                    fields.get("body") or "",
                    fields.get("sent_at"),
                    fields.get("delivered_at"),
                    fields.get("opened_at"),
                    fields.get("clicked_at"),
                    1 if fields.get("bounced") else 0,
                    now,
                ),
            )
            self._conn.commit()
        return self._fetchone("SELECT * FROM outreach_messages WHERE id = ?", (msg_id,))  # type: ignore[return-value]

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
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO outreach_replies (
                    id, lead_id, message_id, from_address, subject, body,
                    classification, confidence, resolved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reply_id,
                    fields.get("lead_id"),
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
        return self._fetchone("SELECT * FROM outreach_replies WHERE id = ?", (reply_id,))  # type: ignore[return-value]

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
