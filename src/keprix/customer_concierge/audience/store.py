"""Durable audience identity/session store (Prompt 630)."""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.customer_concierge.audience.models import (
    AudienceIdentity,
    AudienceSession,
    _now,
    is_audience_session_usable,
)
from keprix.customer_concierge.store import default_db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audience_identities (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    external_key TEXT NOT NULL,
    display_name TEXT,
    email TEXT,
    phone TEXT,
    crm_contact_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, channel, external_key)
);

CREATE TABLE IF NOT EXISTS audience_sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    concierge_profile_id TEXT,
    identity_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    session_mode TEXT NOT NULL DEFAULT 'public',
    widget_session_token TEXT,
    origin TEXT,
    locale TEXT,
    consent_state TEXT NOT NULL DEFAULT 'unknown',
    risk_state TEXT NOT NULL DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'active',
    expires_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    active_support_case_id TEXT,
    handed_off_at TEXT,
    operator_user_id TEXT,
    conversation_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_audience_sessions_ws
    ON audience_sessions(workspace_id, persona_id);
CREATE INDEX IF NOT EXISTS idx_audience_sessions_token
    ON audience_sessions(widget_session_token);

CREATE TABLE IF NOT EXISTS audience_rate_buckets (
    bucket_key TEXT PRIMARY KEY,
    hit_count INTEGER NOT NULL DEFAULT 0,
    reset_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audience_embed_nonces (
    nonce TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);

CREATE TABLE IF NOT EXISTS audience_audit_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    session_id TEXT,
    identity_id TEXT,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL DEFAULT 'system',
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audience_audit_ws
    ON audience_audit_events(workspace_id, created_at);
"""

DEFAULT_TTL_HOURS = 24 * 30
_lock = threading.Lock()
_store: AudienceStore | None = None


class AudienceStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or default_db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_SCHEMA)
            self._migrate_session_columns()

    def _migrate_session_columns(self) -> None:
        cur = self._conn.execute("PRAGMA table_info(audience_sessions)")
        cols = {str(r[1]) for r in cur.fetchall()}
        alters = []
        if "active_support_case_id" not in cols:
            alters.append("ALTER TABLE audience_sessions ADD COLUMN active_support_case_id TEXT")
        if "handed_off_at" not in cols:
            alters.append("ALTER TABLE audience_sessions ADD COLUMN handed_off_at TEXT")
        if "operator_user_id" not in cols:
            alters.append("ALTER TABLE audience_sessions ADD COLUMN operator_user_id TEXT")
        if "conversation_summary" not in cols:
            alters.append("ALTER TABLE audience_sessions ADD COLUMN conversation_summary TEXT")
        for stmt in alters:
            self._conn.execute(stmt)
        if alters:
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def mark_handed_off(
        self,
        *,
        workspace_id: str,
        session_id: str,
        case_id: str | None,
        summary: str | None,
        handed_off_at: str | None = None,
    ) -> AudienceSession | None:
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                UPDATE audience_sessions SET
                  status='handed_off',
                  active_support_case_id=COALESCE(?, active_support_case_id),
                  conversation_summary=COALESCE(?, conversation_summary),
                  handed_off_at=COALESCE(handed_off_at, ?),
                  last_active_at=?
                WHERE workspace_id=? AND id=?
                """,
                (case_id, summary, handed_off_at or now, now, workspace_id, session_id),
            )
        return self.get_session(workspace_id, session_id)

    def set_operator(
        self, *, workspace_id: str, session_id: str, operator_user_id: str | None
    ) -> AudienceSession | None:
        now = _now()
        status = "handed_off" if operator_user_id else "active"
        with self._conn:
            self._conn.execute(
                """
                UPDATE audience_sessions SET
                  operator_user_id=?, status=?, last_active_at=?
                WHERE workspace_id=? AND id=?
                """,
                (operator_user_id, status, now, workspace_id, session_id),
            )
        return self.get_session(workspace_id, session_id)

    def upsert_identity(
        self,
        *,
        workspace_id: str,
        channel: str,
        external_key: str,
        display_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        crm_contact_id: str | None = None,
    ) -> AudienceIdentity:
        now = _now()
        cur = self._conn.execute(
            """
            SELECT * FROM audience_identities
            WHERE workspace_id=? AND channel=? AND external_key=?
            """,
            (workspace_id, channel, external_key),
        )
        row = cur.fetchone()
        if row:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE audience_identities SET
                      display_name=COALESCE(?, display_name),
                      email=COALESCE(?, email),
                      phone=COALESCE(?, phone),
                      crm_contact_id=COALESCE(?, crm_contact_id),
                      updated_at=?
                    WHERE id=?
                    """,
                    (display_name, email, phone, crm_contact_id, now, row["id"]),
                )
            return self.get_identity(workspace_id, str(row["id"]))  # type: ignore[return-value]

        iid = str(uuid4())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO audience_identities (
                  id, workspace_id, channel, external_key, display_name, email, phone,
                  crm_contact_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    iid,
                    workspace_id,
                    channel,
                    external_key,
                    display_name,
                    email,
                    phone,
                    crm_contact_id,
                    now,
                    now,
                ),
            )
        return self.get_identity(workspace_id, iid)  # type: ignore[return-value]

    def get_identity(self, workspace_id: str, identity_id: str) -> AudienceIdentity | None:
        cur = self._conn.execute(
            "SELECT * FROM audience_identities WHERE workspace_id=? AND id=?",
            (workspace_id, identity_id),
        )
        row = cur.fetchone()
        return self._map_identity(row) if row else None

    def create_session(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        concierge_profile_id: str | None,
        identity_id: str,
        channel: str = "web",
        session_mode: str = "public",
        origin: str | None = None,
        locale: str | None = None,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        consent_state: str = "unknown",
    ) -> AudienceSession:
        # Cross-tenant: identity must belong to workspace
        identity = self.get_identity(workspace_id, identity_id)
        if not identity:
            raise PermissionError("workspace_mismatch:identity")

        sid = str(uuid4())
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires = now + timedelta(hours=ttl_hours)
        now_s = now.isoformat()
        exp_s = expires.isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO audience_sessions (
                  id, workspace_id, persona_id, concierge_profile_id, identity_id, channel,
                  session_mode, widget_session_token, origin, locale, consent_state,
                  risk_state, status, expires_at, last_active_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'normal', 'active', ?, ?, ?)
                """,
                (
                    sid,
                    workspace_id,
                    persona_id,
                    concierge_profile_id,
                    identity_id,
                    channel,
                    session_mode,
                    token,
                    origin,
                    locale,
                    consent_state,
                    exp_s,
                    now_s,
                    now_s,
                ),
            )
        self.append_audit(
            workspace_id=workspace_id,
            session_id=sid,
            identity_id=identity_id,
            event_type="conversation.started",
            actor_type="audience",
            detail={"channel": channel, "sessionMode": session_mode},
        )
        return self.get_session(workspace_id, sid)  # type: ignore[return-value]

    def get_session(self, workspace_id: str, session_id: str) -> AudienceSession | None:
        cur = self._conn.execute(
            "SELECT * FROM audience_sessions WHERE workspace_id=? AND id=?",
            (workspace_id, session_id),
        )
        row = cur.fetchone()
        return self._map_session(row) if row else None

    def get_session_by_token(self, token: str) -> AudienceSession | None:
        cur = self._conn.execute(
            "SELECT * FROM audience_sessions WHERE widget_session_token=?",
            (token,),
        )
        row = cur.fetchone()
        return self._map_session(row) if row else None

    def touch_session(self, workspace_id: str, session_id: str) -> None:
        with self._conn:
            self._conn.execute(
                """
                UPDATE audience_sessions SET last_active_at=?
                WHERE workspace_id=? AND id=?
                """,
                (_now(), workspace_id, session_id),
            )

    def set_risk(self, workspace_id: str, session_id: str, risk_state: str) -> AudienceSession | None:
        with self._conn:
            self._conn.execute(
                "UPDATE audience_sessions SET risk_state=? WHERE workspace_id=? AND id=?",
                (risk_state, workspace_id, session_id),
            )
        return self.get_session(workspace_id, session_id)

    def set_consent(
        self, workspace_id: str, session_id: str, consent_state: str
    ) -> AudienceSession | None:
        with self._conn:
            self._conn.execute(
                "UPDATE audience_sessions SET consent_state=? WHERE workspace_id=? AND id=?",
                (consent_state, workspace_id, session_id),
            )
        return self.get_session(workspace_id, session_id)

    def consume_rate_bucket(
        self, bucket_key: str, *, limit: int, window_ms: int
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        reset_at = (now + timedelta(milliseconds=window_ms)).isoformat()
        cur = self._conn.execute(
            "SELECT hit_count, reset_at FROM audience_rate_buckets WHERE bucket_key=?",
            (bucket_key,),
        )
        row = cur.fetchone()
        if not row:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO audience_rate_buckets (bucket_key, hit_count, reset_at, updated_at)
                    VALUES (?, 1, ?, ?)
                    """,
                    (bucket_key, reset_at, _now()),
                )
            return {"allowed": True, "remaining": limit - 1, "resetAt": reset_at}

        try:
            row_reset = datetime.fromisoformat(str(row["reset_at"]).replace("Z", "+00:00"))
        except Exception:
            row_reset = now
        if row_reset.tzinfo is None:
            row_reset = row_reset.replace(tzinfo=timezone.utc)
        if row_reset <= now:
            hit = 1
            new_reset = reset_at
        else:
            hit = int(row["hit_count"]) + 1
            new_reset = str(row["reset_at"])
        with self._conn:
            self._conn.execute(
                """
                UPDATE audience_rate_buckets SET hit_count=?, reset_at=?, updated_at=?
                WHERE bucket_key=?
                """,
                (hit, new_reset, _now(), bucket_key),
            )
        if hit > limit:
            return {"allowed": False, "remaining": 0, "resetAt": new_reset}
        return {"allowed": True, "remaining": max(0, limit - hit), "resetAt": new_reset}

    def consume_embed_nonce(
        self, *, nonce: str, workspace_id: str, persona_id: str, ttl_ms: int = 900_000
    ) -> bool:
        cur = self._conn.execute(
            "SELECT nonce FROM audience_embed_nonces WHERE nonce=?",
            (nonce,),
        )
        if cur.fetchone():
            return False
        expires = (datetime.now(timezone.utc) + timedelta(milliseconds=ttl_ms)).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO audience_embed_nonces (nonce, persona_id, workspace_id, expires_at, consumed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nonce, persona_id, workspace_id, expires, _now()),
            )
        return True

    def append_audit(
        self,
        *,
        workspace_id: str,
        event_type: str,
        actor_type: str = "system",
        session_id: str | None = None,
        identity_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO audience_audit_events (
                  id, workspace_id, session_id, identity_id, event_type, actor_type, detail_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    workspace_id,
                    session_id,
                    identity_id,
                    event_type,
                    actor_type,
                    json.dumps(detail or {}),
                    _now(),
                ),
            )

    def list_audit(self, workspace_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM audience_audit_events
            WHERE workspace_id=?
            ORDER BY created_at DESC LIMIT ?
            """,
            (workspace_id, limit),
        )
        out = []
        for row in cur.fetchall():
            out.append(
                {
                    "id": row["id"],
                    "workspaceId": row["workspace_id"],
                    "sessionId": row["session_id"],
                    "identityId": row["identity_id"],
                    "eventType": row["event_type"],
                    "actorType": row["actor_type"],
                    "detail": json.loads(row["detail_json"] or "{}"),
                    "createdAt": row["created_at"],
                }
            )
        return out

    def export_identity(self, workspace_id: str, identity_id: str) -> dict[str, Any] | None:
        identity = self.get_identity(workspace_id, identity_id)
        if not identity:
            return None
        cur = self._conn.execute(
            "SELECT * FROM audience_sessions WHERE workspace_id=? AND identity_id=?",
            (workspace_id, identity_id),
        )
        sessions = [self._map_session(r).to_dict() for r in cur.fetchall()]  # type: ignore[union-attr]
        return {"identity": identity.to_dict(), "sessions": sessions}

    def erase_identity(self, workspace_id: str, identity_id: str) -> dict[str, Any]:
        with self._conn:
            cur_s = self._conn.execute(
                "DELETE FROM audience_sessions WHERE workspace_id=? AND identity_id=?",
                (workspace_id, identity_id),
            )
            cur_i = self._conn.execute(
                "DELETE FROM audience_identities WHERE workspace_id=? AND id=?",
                (workspace_id, identity_id),
            )
        self.append_audit(
            workspace_id=workspace_id,
            identity_id=identity_id,
            event_type="privacy.erase",
            actor_type="operator",
            detail={"sessionsDeleted": cur_s.rowcount, "identityDeleted": cur_i.rowcount > 0},
        )
        return {
            "sessionsDeleted": cur_s.rowcount,
            "identityDeleted": cur_i.rowcount > 0,
        }

    def list_identities(self, workspace_id: str) -> list[AudienceIdentity]:
        cur = self._conn.execute(
            "SELECT * FROM audience_identities WHERE workspace_id=? ORDER BY created_at ASC",
            (workspace_id,),
        )
        return [self._map_identity(r) for r in cur.fetchall()]  # type: ignore[misc]

    @staticmethod
    def _map_identity(row: sqlite3.Row | None) -> AudienceIdentity | None:
        if not row:
            return None
        return AudienceIdentity(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            channel=str(row["channel"]),
            external_key=str(row["external_key"]),
            display_name=row["display_name"],
            email=row["email"],
            phone=row["phone"],
            crm_contact_id=row["crm_contact_id"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _map_session(row: sqlite3.Row | None) -> AudienceSession | None:
        if not row:
            return None
        keys = row.keys()
        return AudienceSession(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            persona_id=str(row["persona_id"]),
            concierge_profile_id=row["concierge_profile_id"],
            identity_id=str(row["identity_id"]),
            channel=str(row["channel"]),
            session_mode=str(row["session_mode"]),  # type: ignore[arg-type]
            widget_session_token=row["widget_session_token"],
            origin=row["origin"],
            locale=row["locale"],
            consent_state=str(row["consent_state"]),  # type: ignore[arg-type]
            risk_state=str(row["risk_state"]),  # type: ignore[arg-type]
            status=str(row["status"]),  # type: ignore[arg-type]
            expires_at=str(row["expires_at"]),
            last_active_at=str(row["last_active_at"]),
            created_at=str(row["created_at"]),
            active_support_case_id=row["active_support_case_id"]
            if "active_support_case_id" in keys
            else None,
            handed_off_at=row["handed_off_at"] if "handed_off_at" in keys else None,
            operator_user_id=row["operator_user_id"] if "operator_user_id" in keys else None,
            conversation_summary=row["conversation_summary"]
            if "conversation_summary" in keys
            else None,
        )


def get_audience_store(path: Path | None = None) -> AudienceStore:
    global _store
    with _lock:
        if path is not None:
            return AudienceStore(path=path)
        if _store is None:
            _store = AudienceStore()
        return _store


def reset_audience_store_for_tests(path: Path | None = None) -> AudienceStore:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = AudienceStore(path=path) if path else AudienceStore()
        return _store


__all__ = [
    "AudienceStore",
    "get_audience_store",
    "is_audience_session_usable",
    "reset_audience_store_for_tests",
]
