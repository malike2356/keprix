"""Durable calendar projections, delivery attempts, watches, outbox (Prompt 633)."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vical_calendar_projections (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    booking_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_event_id TEXT,
    etag TEXT,
    html_link TEXT,
    host_event_created INTEGER NOT NULL DEFAULT 0,
    invitation_send_requested INTEGER NOT NULL DEFAULT 0,
    invitation_delivery_state TEXT NOT NULL DEFAULT 'unknown',
    attendees_json TEXT NOT NULL DEFAULT '[]',
    workspace_event_id TEXT,
    ics_uid TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    detail TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, booking_id, provider)
);

CREATE TABLE IF NOT EXISTS vical_delivery_attempts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    booking_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence TEXT,
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vical_calendar_watch_channels (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    resource_id TEXT,
    expiration_at TEXT NOT NULL,
    sync_token TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, provider, channel_id)
);

CREATE TABLE IF NOT EXISTS vical_notification_outbox (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    booking_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    to_address TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    evidence TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    delivered_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_vical_proj_booking
    ON vical_calendar_projections(workspace_id, booking_id);
CREATE INDEX IF NOT EXISTS idx_vical_outbox_status
    ON vical_notification_outbox(status, created_at);
"""

_lock = threading.Lock()
_store: ProjectionStore | None = None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_projection_db_path() -> Path:
    override = (os.environ.get("KEPRIX_VICAL_CALENDAR_DB_PATH") or "").strip()
    if override:
        return Path(override)
    # Share saga DB when present for CE simplicity
    saga = (os.environ.get("KEPRIX_VICAL_SAGA_DB_PATH") or "").strip()
    if saga:
        return Path(saga)
    home = Path(os.environ.get("KEPRIX_HOME") or Path.home() / ".keprix")
    data = Path(os.environ.get("KEPRIX_DATA_DIR") or home / "data")
    return data / "vical_saga.sqlite"


class ProjectionStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or default_projection_db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def upsert_projection(
        self,
        *,
        workspace_id: str,
        user_id: str,
        booking_id: str,
        provider: str,
        provider_event_id: str | None = None,
        etag: str | None = None,
        html_link: str | None = None,
        host_event_created: bool = False,
        invitation_send_requested: bool = False,
        invitation_delivery_state: str = "unknown",
        attendees: list[dict[str, Any]] | None = None,
        workspace_event_id: str | None = None,
        ics_uid: str | None = None,
        status: str = "succeeded",
        detail: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        cur = self._conn.execute(
            """
            SELECT id FROM vical_calendar_projections
            WHERE workspace_id=? AND booking_id=? AND provider=?
            """,
            (workspace_id, booking_id, provider),
        )
        row = cur.fetchone()
        payload = (
            provider_event_id,
            etag,
            html_link,
            1 if host_event_created else 0,
            1 if invitation_send_requested else 0,
            invitation_delivery_state,
            json.dumps(attendees or []),
            workspace_event_id,
            ics_uid,
            status,
            detail,
            now,
        )
        if row:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE vical_calendar_projections SET
                      provider_event_id=COALESCE(?, provider_event_id),
                      etag=COALESCE(?, etag),
                      html_link=COALESCE(?, html_link),
                      host_event_created=?,
                      invitation_send_requested=?,
                      invitation_delivery_state=?,
                      attendees_json=?,
                      workspace_event_id=COALESCE(?, workspace_event_id),
                      ics_uid=COALESCE(?, ics_uid),
                      status=?,
                      detail=?,
                      updated_at=?
                    WHERE id=?
                    """,
                    (*payload, row["id"]),
                )
        else:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO vical_calendar_projections (
                      id, workspace_id, user_id, booking_id, provider,
                      provider_event_id, etag, html_link, host_event_created,
                      invitation_send_requested, invitation_delivery_state,
                      attendees_json, workspace_event_id, ics_uid, status, detail,
                      created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        workspace_id,
                        user_id,
                        booking_id,
                        provider,
                        *payload[:-1],
                        now,
                        now,
                    ),
                )
        return self.get_projection(workspace_id, booking_id, provider=provider)  # type: ignore[return-value]

    def get_projection(
        self, workspace_id: str, booking_id: str, *, provider: str | None = None
    ) -> dict[str, Any] | None:
        if provider:
            cur = self._conn.execute(
                """
                SELECT * FROM vical_calendar_projections
                WHERE workspace_id=? AND booking_id=? AND provider=?
                """,
                (workspace_id, booking_id, provider),
            )
        else:
            cur = self._conn.execute(
                """
                SELECT * FROM vical_calendar_projections
                WHERE workspace_id=? AND booking_id=?
                ORDER BY CASE provider WHEN 'google' THEN 0 WHEN 'microsoft' THEN 1 ELSE 2 END,
                         updated_at DESC
                LIMIT 1
                """,
                (workspace_id, booking_id),
            )
        row = cur.fetchone()
        return self._map_projection(row) if row else None

    def record_delivery_attempt(
        self,
        *,
        workspace_id: str,
        booking_id: str,
        channel: str,
        provider: str,
        status: str,
        evidence: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        aid = str(uuid4())
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO vical_delivery_attempts (
                  id, workspace_id, booking_id, channel, provider, status,
                  evidence, detail_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    aid,
                    workspace_id,
                    booking_id,
                    channel,
                    provider,
                    status,
                    evidence,
                    json.dumps(detail or {}),
                    now,
                ),
            )
        return {
            "id": aid,
            "channel": channel,
            "provider": provider,
            "status": status,
            "evidence": evidence,
            "createdAt": now,
        }

    def list_delivery_attempts(self, workspace_id: str, booking_id: str) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM vical_delivery_attempts
            WHERE workspace_id=? AND booking_id=?
            ORDER BY created_at ASC
            """,
            (workspace_id, booking_id),
        )
        return [
            {
                "id": r["id"],
                "channel": r["channel"],
                "provider": r["provider"],
                "status": r["status"],
                "evidence": r["evidence"],
                "detail": json.loads(r["detail_json"] or "{}"),
                "createdAt": r["created_at"],
            }
            for r in cur.fetchall()
        ]

    def upsert_watch(
        self,
        *,
        workspace_id: str,
        user_id: str,
        provider: str,
        channel_id: str,
        resource_id: str | None,
        expiration_at: str,
        sync_token: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO vical_calendar_watch_channels (
                  id, workspace_id, user_id, provider, channel_id, resource_id,
                  expiration_at, sync_token, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                ON CONFLICT(workspace_id, provider, channel_id) DO UPDATE SET
                  resource_id=excluded.resource_id,
                  expiration_at=excluded.expiration_at,
                  sync_token=COALESCE(excluded.sync_token, sync_token),
                  status='active',
                  updated_at=excluded.updated_at
                """,
                (
                    str(uuid4()),
                    workspace_id,
                    user_id,
                    provider,
                    channel_id,
                    resource_id,
                    expiration_at,
                    sync_token,
                    now,
                    now,
                ),
            )
        return {
            "channelId": channel_id,
            "expirationAt": expiration_at,
            "provider": provider,
            "status": "active",
        }

    def list_expiring_watches(self, *, within_seconds: int = 3600) -> list[dict[str, Any]]:
        cutoff = (
            datetime.now(timezone.utc) + timedelta(seconds=within_seconds)
        ).replace(microsecond=0).isoformat()
        cur = self._conn.execute(
            """
            SELECT * FROM vical_calendar_watch_channels
            WHERE status='active' AND expiration_at <= ?
            """,
            (cutoff,),
        )
        return [
            {
                "id": r["id"],
                "workspaceId": r["workspace_id"],
                "userId": r["user_id"],
                "provider": r["provider"],
                "channelId": r["channel_id"],
                "resourceId": r["resource_id"],
                "expirationAt": r["expiration_at"],
                "syncToken": r["sync_token"],
            }
            for r in cur.fetchall()
        ]

    def renew_watch(self, workspace_id: str, channel_id: str, *, expiration_at: str) -> bool:
        with self._conn:
            cur = self._conn.execute(
                """
                UPDATE vical_calendar_watch_channels
                SET expiration_at=?, updated_at=?, status='active'
                WHERE workspace_id=? AND channel_id=?
                """,
                (expiration_at, _now(), workspace_id, channel_id),
            )
        return cur.rowcount > 0

    def enqueue_notification(
        self,
        *,
        workspace_id: str,
        booking_id: str,
        channel: str,
        to_address: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        nid = str(uuid4())
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO vical_notification_outbox (
                  id, workspace_id, booking_id, channel, to_address, subject, body,
                  status, attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?)
                """,
                (nid, workspace_id, booking_id, channel, to_address, subject, body, now, now),
            )
        return {"id": nid, "status": "pending", "channel": channel}

    def mark_notification(
        self,
        notification_id: str,
        *,
        status: str,
        evidence: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any] | None:
        now = _now()
        delivered = now if status in {"sent", "delivered"} else None
        with self._conn:
            self._conn.execute(
                """
                UPDATE vical_notification_outbox SET
                  status=?, evidence=COALESCE(?, evidence), last_error=?,
                  attempts=attempts+1, updated_at=?, delivered_at=COALESCE(?, delivered_at)
                WHERE id=?
                """,
                (status, evidence, error, now, delivered, notification_id),
            )
        cur = self._conn.execute(
            "SELECT * FROM vical_notification_outbox WHERE id=?", (notification_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "status": row["status"],
            "evidence": row["evidence"],
            "attempts": row["attempts"],
            "channel": row["channel"],
            "deliveredAt": row["delivered_at"],
        }

    def list_pending_notifications(self, *, limit: int = 50) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM vical_notification_outbox
            WHERE status='pending'
            ORDER BY created_at ASC LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "id": r["id"],
                "workspaceId": r["workspace_id"],
                "bookingId": r["booking_id"],
                "channel": r["channel"],
                "toAddress": r["to_address"],
                "subject": r["subject"],
                "body": r["body"],
                "status": r["status"],
            }
            for r in cur.fetchall()
        ]

    @staticmethod
    def _map_projection(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "workspaceId": row["workspace_id"],
            "userId": row["user_id"],
            "bookingId": row["booking_id"],
            "provider": row["provider"],
            "providerEventId": row["provider_event_id"],
            "etag": row["etag"],
            "htmlLink": row["html_link"],
            "hostEventCreated": bool(row["host_event_created"]),
            "invitationSendRequested": bool(row["invitation_send_requested"]),
            "invitationDeliveryState": row["invitation_delivery_state"],
            "attendees": json.loads(row["attendees_json"] or "[]"),
            "workspaceEventId": row["workspace_event_id"],
            "icsUid": row["ics_uid"],
            "status": row["status"],
            "detail": row["detail"],
            "updatedAt": row["updated_at"],
        }


def get_projection_store(path: Path | None = None) -> ProjectionStore:
    global _store
    with _lock:
        if path is not None:
            return ProjectionStore(path=path)
        if _store is None:
            _store = ProjectionStore()
        return _store


def reset_projection_store_for_tests(path: Path | None = None) -> ProjectionStore:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = ProjectionStore(path=path) if path else ProjectionStore()
        return _store
