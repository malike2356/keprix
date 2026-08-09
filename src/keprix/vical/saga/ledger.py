"""Durable saga ledger for booking holds, intents, artifacts, ops (Prompt 632)."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vical_availability_holds (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    event_type_id TEXT,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    holder_token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'held',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vical_booking_intents (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    booking_id TEXT,
    guest_email TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS vical_booking_participants (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    booking_id TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT,
    display_name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vical_conference_artifacts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    booking_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    meeting_id TEXT,
    join_url TEXT,
    host_start_url TEXT,
    passcode TEXT,
    managed INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, booking_id, provider)
);

CREATE TABLE IF NOT EXISTS vical_provider_operations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    booking_id TEXT,
    provider TEXT NOT NULL,
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    error_code TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(workspace_id, provider, operation, idempotency_key)
);

CREATE TABLE IF NOT EXISTS vical_webhook_receipts (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(provider, event_id)
);
"""

_lock = threading.Lock()
_store: SagaLedger | None = None


def default_saga_db_path() -> Path:
    override = (os.environ.get("KEPRIX_VICAL_SAGA_DB_PATH") or "").strip()
    if override:
        return Path(override)
    home = Path(os.environ.get("KEPRIX_HOME") or Path.home() / ".keprix")
    data = Path(os.environ.get("KEPRIX_DATA_DIR") or home / "data")
    return data / "vical_saga.sqlite"


class SagaLedger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or default_saga_db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def create_hold(
        self,
        *,
        workspace_id: str,
        user_id: str,
        starts_at: str,
        ends_at: str,
        holder_token: str,
        expires_at: str,
        event_type_id: str | None = None,
    ) -> dict[str, Any]:
        hid = str(uuid4())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO vical_availability_holds (
                  id, workspace_id, user_id, event_type_id, starts_at, ends_at,
                  holder_token, expires_at, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'held', ?)
                """,
                (
                    hid,
                    workspace_id,
                    user_id,
                    event_type_id,
                    starts_at,
                    ends_at,
                    holder_token,
                    expires_at,
                    _now(),
                ),
            )
        return {"id": hid, "holderToken": holder_token, "status": "held"}

    def release_hold(self, workspace_id: str, hold_id: str) -> None:
        with self._conn:
            self._conn.execute(
                """
                UPDATE vical_availability_holds SET status='released'
                WHERE workspace_id=? AND id=?
                """,
                (workspace_id, hold_id),
            )

    def find_booking_by_idempotency(
        self, workspace_id: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        cur = self._conn.execute(
            """
            SELECT * FROM vical_booking_intents
            WHERE workspace_id=? AND idempotency_key=?
            """,
            (workspace_id, idempotency_key),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "bookingId": row["booking_id"],
            "status": row["status"],
            "idempotencyKey": row["idempotency_key"],
            "payload": json.loads(row["payload_json"] or "{}"),
        }

    def upsert_intent(
        self,
        *,
        workspace_id: str,
        user_id: str,
        idempotency_key: str,
        guest_email: str,
        starts_at: str,
        payload: dict[str, Any] | None = None,
        booking_id: str | None = None,
        status: str = "open",
    ) -> dict[str, Any]:
        existing = self.find_booking_by_idempotency(workspace_id, idempotency_key)
        now = _now()
        if existing:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE vical_booking_intents SET
                      booking_id=COALESCE(?, booking_id),
                      status=?,
                      payload_json=?,
                      updated_at=?
                    WHERE workspace_id=? AND idempotency_key=?
                    """,
                    (
                        booking_id,
                        status,
                        json.dumps(payload or existing.get("payload") or {}),
                        now,
                        workspace_id,
                        idempotency_key,
                    ),
                )
            return self.find_booking_by_idempotency(workspace_id, idempotency_key)  # type: ignore[return-value]

        iid = str(uuid4())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO vical_booking_intents (
                  id, workspace_id, user_id, idempotency_key, booking_id, guest_email,
                  starts_at, status, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    iid,
                    workspace_id,
                    user_id,
                    idempotency_key,
                    booking_id,
                    guest_email,
                    starts_at,
                    status,
                    json.dumps(payload or {}),
                    now,
                    now,
                ),
            )
        return self.find_booking_by_idempotency(workspace_id, idempotency_key)  # type: ignore[return-value]

    def commit_intent(
        self, workspace_id: str, idempotency_key: str, booking_id: str
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                UPDATE vical_booking_intents SET booking_id=?, status='committed', updated_at=?
                WHERE workspace_id=? AND idempotency_key=?
                """,
                (booking_id, _now(), workspace_id, idempotency_key),
            )

    def add_participants(
        self,
        *,
        workspace_id: str,
        booking_id: str,
        participants: list[dict[str, Any]],
    ) -> None:
        now = _now()
        with self._conn:
            for p in participants:
                self._conn.execute(
                    """
                    INSERT INTO vical_booking_participants (
                      id, workspace_id, booking_id, role, email, display_name, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        workspace_id,
                        booking_id,
                        str(p.get("role") or "guest"),
                        p.get("email"),
                        p.get("displayName") or p.get("name"),
                        now,
                    ),
                )

    def upsert_conference_artifact(
        self,
        *,
        workspace_id: str,
        booking_id: str,
        provider: str,
        status: str,
        meeting_id: str | None = None,
        join_url: str | None = None,
        host_start_url: str | None = None,
        passcode: str | None = None,
        managed: bool = False,
        detail: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        cur = self._conn.execute(
            """
            SELECT id FROM vical_conference_artifacts
            WHERE workspace_id=? AND booking_id=? AND provider=?
            """,
            (workspace_id, booking_id, provider),
        )
        row = cur.fetchone()
        if row:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE vical_conference_artifacts SET
                      meeting_id=?, join_url=?, host_start_url=?, passcode=?,
                      managed=?, status=?, detail=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        meeting_id,
                        join_url,
                        host_start_url,
                        passcode,
                        1 if managed else 0,
                        status,
                        detail,
                        now,
                        row["id"],
                    ),
                )
            aid = str(row["id"])
        else:
            aid = str(uuid4())
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO vical_conference_artifacts (
                      id, workspace_id, booking_id, provider, meeting_id, join_url,
                      host_start_url, passcode, managed, status, detail, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        aid,
                        workspace_id,
                        booking_id,
                        provider,
                        meeting_id,
                        join_url,
                        host_start_url,
                        passcode,
                        1 if managed else 0,
                        status,
                        detail,
                        now,
                        now,
                    ),
                )
        return self.get_conference_artifact(workspace_id, booking_id, provider=provider)  # type: ignore[return-value]

    def get_conference_artifact(
        self, workspace_id: str, booking_id: str, *, provider: str | None = None
    ) -> dict[str, Any] | None:
        if provider:
            cur = self._conn.execute(
                """
                SELECT * FROM vical_conference_artifacts
                WHERE workspace_id=? AND booking_id=? AND provider=?
                """,
                (workspace_id, booking_id, provider),
            )
        else:
            cur = self._conn.execute(
                """
                SELECT * FROM vical_conference_artifacts
                WHERE workspace_id=? AND booking_id=?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (workspace_id, booking_id),
            )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "workspaceId": row["workspace_id"],
            "bookingId": row["booking_id"],
            "provider": row["provider"],
            "meetingId": row["meeting_id"],
            "joinUrl": row["join_url"],
            # host_start_url kept in DB only; omit from default public mapping
            "hasHostStartUrl": bool(row["host_start_url"]),
            "passcode": row["passcode"],
            "managed": bool(row["managed"]),
            "status": row["status"],
            "detail": row["detail"],
        }

    def record_provider_operation(
        self,
        *,
        workspace_id: str,
        provider: str,
        operation: str,
        idempotency_key: str,
        status: str,
        booking_id: str | None = None,
        request: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
        error_code: str | None = None,
        attempt: int = 1,
    ) -> dict[str, Any]:
        from keprix.vical.conferencing.redact import redact_conferencing_payload

        oid = str(uuid4())
        try:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO vical_provider_operations (
                      id, workspace_id, booking_id, provider, operation, idempotency_key,
                      status, attempt, request_json, response_json, error_code, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        oid,
                        workspace_id,
                        booking_id,
                        provider,
                        operation,
                        idempotency_key,
                        status,
                        attempt,
                        json.dumps(redact_conferencing_payload(request or {})),
                        json.dumps(redact_conferencing_payload(response or {})),
                        error_code,
                        _now(),
                    ),
                )
        except sqlite3.IntegrityError:
            cur = self._conn.execute(
                """
                SELECT id, status, booking_id FROM vical_provider_operations
                WHERE workspace_id=? AND provider=? AND operation=? AND idempotency_key=?
                """,
                (workspace_id, provider, operation, idempotency_key),
            )
            row = cur.fetchone()
            return {
                "id": row["id"] if row else oid,
                "status": row["status"] if row else status,
                "duplicate": True,
                "bookingId": row["booking_id"] if row else booking_id,
            }
        return {"id": oid, "status": status, "duplicate": False, "bookingId": booking_id}

    def list_provider_operations(self, workspace_id: str, booking_id: str) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM vical_provider_operations
            WHERE workspace_id=? AND booking_id=?
            ORDER BY created_at ASC
            """,
            (workspace_id, booking_id),
        )
        return [
            {
                "id": r["id"],
                "provider": r["provider"],
                "operation": r["operation"],
                "status": r["status"],
                "idempotencyKey": r["idempotency_key"],
                "errorCode": r["error_code"],
                "attempt": r["attempt"],
                "createdAt": r["created_at"],
            }
            for r in cur.fetchall()
        ]

    def record_webhook_receipt(
        self,
        *,
        provider: str,
        event_id: str,
        event_type: str | None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from keprix.vical.conferencing.redact import redact_conferencing_payload

        try:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO vical_webhook_receipts (
                      id, provider, event_id, event_type, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        provider,
                        event_id,
                        event_type,
                        json.dumps(redact_conferencing_payload(payload or {})),
                        _now(),
                    ),
                )
            return {"ok": True, "duplicate": False, "eventId": event_id}
        except sqlite3.IntegrityError:
            return {"ok": True, "duplicate": True, "eventId": event_id}


def get_saga_ledger(path: Path | None = None) -> SagaLedger:
    global _store
    with _lock:
        if path is not None:
            return SagaLedger(path=path)
        if _store is None:
            _store = SagaLedger()
        return _store


def reset_saga_ledger_for_tests(path: Path | None = None) -> SagaLedger:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = SagaLedger(path=path) if path else SagaLedger()
        return _store


__all__ = [
    "SagaLedger",
    "get_saga_ledger",
    "reset_saga_ledger_for_tests",
]
