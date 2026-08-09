"""Tenant customer-support cases for Concierge visitors (Prompt 631).

Separate from keprix.support (operator product-support tickets). Storage,
routes, and UI labels must never mix the two scopes.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from keprix.customer_concierge.audience.models import _now
from keprix.customer_concierge.store import default_db_path

CaseStatus = Literal["open", "pending_customer", "pending_operator", "resolved", "closed"]
CasePriority = Literal["low", "normal", "high", "urgent"]
SCOPE = "tenant_customer_support"
PRODUCT_SUPPORT_SCOPE = "keprix_product_support"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS concierge_support_cases (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    concierge_profile_id TEXT,
    audience_session_id TEXT,
    identity_id TEXT,
    contact_id TEXT,
    channel TEXT NOT NULL DEFAULT 'web',
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'normal',
    assignee_user_id TEXT,
    sla_first_response_at TEXT,
    sla_resolution_at TEXT,
    first_responded_at TEXT,
    resolved_at TEXT,
    conversation_summary TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    scope TEXT NOT NULL DEFAULT 'tenant_customer_support',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_concierge_cases_ws
    ON concierge_support_cases(workspace_id, persona_id, status);

CREATE TABLE IF NOT EXISTS concierge_support_case_events (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL DEFAULT 'system',
    actor_id TEXT,
    detail TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concierge_internal_notes (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    case_id TEXT,
    audience_session_id TEXT,
    author_user_id TEXT,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_concierge_notes_case
    ON concierge_internal_notes(workspace_id, case_id);

CREATE TABLE IF NOT EXISTS concierge_conversation_messages (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    audience_session_id TEXT NOT NULL,
    case_id TEXT,
    role TEXT NOT NULL,
    body TEXT NOT NULL,
    citations_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
"""

_lock = threading.Lock()
_store: SupportCaseStore | None = None


class SupportCaseStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or default_db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def create_case(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        subject: str,
        channel: str = "web",
        concierge_profile_id: str | None = None,
        audience_session_id: str | None = None,
        identity_id: str | None = None,
        contact_id: str | None = None,
        priority: CasePriority = "normal",
        conversation_summary: str | None = None,
        actor_type: str = "ai",
        metadata: dict[str, Any] | None = None,
        sla_first_response_minutes: int = 60,
        sla_resolution_minutes: int = 1440,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        cid = str(uuid4())
        first = (now + timedelta(minutes=sla_first_response_minutes)).isoformat()
        resolve = (now + timedelta(minutes=sla_resolution_minutes)).isoformat()
        now_s = now.isoformat()
        meta = dict(metadata or {})
        meta["scope"] = SCOPE
        meta["notProductSupport"] = True
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO concierge_support_cases (
                  id, workspace_id, persona_id, concierge_profile_id, audience_session_id,
                  identity_id, contact_id, channel, subject, status, priority,
                  assignee_user_id, sla_first_response_at, sla_resolution_at,
                  first_responded_at, resolved_at, conversation_summary, metadata_json,
                  scope, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, NULL, ?, ?, NULL, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    workspace_id,
                    persona_id,
                    concierge_profile_id,
                    audience_session_id,
                    identity_id,
                    contact_id,
                    channel,
                    subject[:200],
                    priority,
                    first,
                    resolve,
                    conversation_summary,
                    json.dumps(meta),
                    SCOPE,
                    now_s,
                    now_s,
                ),
            )
        self.append_event(
            workspace_id=workspace_id,
            case_id=cid,
            event_type="support_case.opened",
            actor_type=actor_type,
            detail=subject[:200],
            payload={"priority": priority, "channel": channel},
        )
        row = self.get_case(workspace_id, cid)
        assert row is not None
        return row

    def get_case(self, workspace_id: str, case_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute(
            "SELECT * FROM concierge_support_cases WHERE workspace_id=? AND id=?",
            (workspace_id, case_id),
        )
        row = cur.fetchone()
        return self._map_case(row) if row else None

    def list_cases(
        self, workspace_id: str, *, persona_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        if persona_id:
            cur = self._conn.execute(
                """
                SELECT * FROM concierge_support_cases
                WHERE workspace_id=? AND persona_id=? AND scope=?
                ORDER BY created_at DESC LIMIT ?
                """,
                (workspace_id, persona_id, SCOPE, limit),
            )
        else:
            cur = self._conn.execute(
                """
                SELECT * FROM concierge_support_cases
                WHERE workspace_id=? AND scope=?
                ORDER BY created_at DESC LIMIT ?
                """,
                (workspace_id, SCOPE, limit),
            )
        return [self._map_case(r) for r in cur.fetchall()]

    def transition(
        self,
        *,
        workspace_id: str,
        case_id: str,
        status: CaseStatus,
        actor_type: str = "operator",
        actor_id: str | None = None,
    ) -> dict[str, Any] | None:
        case = self.get_case(workspace_id, case_id)
        if not case:
            return None
        now = _now()
        resolved_at = now if status in {"resolved", "closed"} else case.get("resolvedAt")
        with self._conn:
            self._conn.execute(
                """
                UPDATE concierge_support_cases SET status=?, resolved_at=?, updated_at=?
                WHERE workspace_id=? AND id=?
                """,
                (status, resolved_at, now, workspace_id, case_id),
            )
        self.append_event(
            workspace_id=workspace_id,
            case_id=case_id,
            event_type="support_case.status",
            actor_type=actor_type,
            actor_id=actor_id,
            detail=status,
            payload={"from": case["status"], "to": status},
        )
        return self.get_case(workspace_id, case_id)

    def assign(
        self, *, workspace_id: str, case_id: str, assignee_user_id: str
    ) -> dict[str, Any] | None:
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                UPDATE concierge_support_cases SET assignee_user_id=?, updated_at=?
                WHERE workspace_id=? AND id=?
                """,
                (assignee_user_id, now, workspace_id, case_id),
            )
        self.append_event(
            workspace_id=workspace_id,
            case_id=case_id,
            event_type="support_case.assigned",
            actor_type="operator",
            actor_id=assignee_user_id,
            detail=assignee_user_id,
        )
        return self.get_case(workspace_id, case_id)

    def append_event(
        self,
        *,
        workspace_id: str,
        case_id: str,
        event_type: str,
        actor_type: str = "system",
        actor_id: str | None = None,
        detail: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO concierge_support_case_events (
                  id, case_id, workspace_id, event_type, actor_type, actor_id,
                  detail, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    case_id,
                    workspace_id,
                    event_type,
                    actor_type,
                    actor_id,
                    detail,
                    json.dumps(payload or {}),
                    _now(),
                ),
            )

    def list_events(self, workspace_id: str, case_id: str) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM concierge_support_case_events
            WHERE workspace_id=? AND case_id=?
            ORDER BY created_at ASC
            """,
            (workspace_id, case_id),
        )
        out = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": r["id"],
                    "caseId": r["case_id"],
                    "workspaceId": r["workspace_id"],
                    "eventType": r["event_type"],
                    "actorType": r["actor_type"],
                    "actorId": r["actor_id"],
                    "detail": r["detail"],
                    "payload": json.loads(r["payload_json"] or "{}"),
                    "createdAt": r["created_at"],
                }
            )
        return out

    def add_internal_note(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        body: str,
        author_user_id: str | None,
        case_id: str | None = None,
        audience_session_id: str | None = None,
    ) -> dict[str, Any]:
        nid = str(uuid4())
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO concierge_internal_notes (
                  id, workspace_id, persona_id, case_id, audience_session_id,
                  author_user_id, body, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nid,
                    workspace_id,
                    persona_id,
                    case_id,
                    audience_session_id,
                    author_user_id,
                    body,
                    now,
                ),
            )
        return {
            "id": nid,
            "workspaceId": workspace_id,
            "personaId": persona_id,
            "caseId": case_id,
            "audienceSessionId": audience_session_id,
            "authorUserId": author_user_id,
            "body": body,
            "visibility": "owner_only",
            "createdAt": now,
        }

    def list_internal_notes(
        self, workspace_id: str, *, case_id: str | None = None
    ) -> list[dict[str, Any]]:
        if case_id:
            cur = self._conn.execute(
                """
                SELECT * FROM concierge_internal_notes
                WHERE workspace_id=? AND case_id=?
                ORDER BY created_at ASC
                """,
                (workspace_id, case_id),
            )
        else:
            cur = self._conn.execute(
                """
                SELECT * FROM concierge_internal_notes
                WHERE workspace_id=?
                ORDER BY created_at DESC LIMIT 100
                """,
                (workspace_id,),
            )
        return [
            {
                "id": r["id"],
                "workspaceId": r["workspace_id"],
                "personaId": r["persona_id"],
                "caseId": r["case_id"],
                "audienceSessionId": r["audience_session_id"],
                "authorUserId": r["author_user_id"],
                "body": r["body"],
                "visibility": "owner_only",
                "createdAt": r["created_at"],
            }
            for r in cur.fetchall()
        ]

    def append_message(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        audience_session_id: str,
        role: str,
        body: str,
        case_id: str | None = None,
        citations: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mid = str(uuid4())
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO concierge_conversation_messages (
                  id, workspace_id, persona_id, audience_session_id, case_id,
                  role, body, citations_json, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mid,
                    workspace_id,
                    persona_id,
                    audience_session_id,
                    case_id,
                    role,
                    body,
                    json.dumps(citations or []),
                    json.dumps(metadata or {}),
                    now,
                ),
            )
        return {
            "id": mid,
            "workspaceId": workspace_id,
            "personaId": persona_id,
            "audienceSessionId": audience_session_id,
            "caseId": case_id,
            "role": role,
            "body": body,
            "citations": citations or [],
            "createdAt": now,
        }

    def list_messages(
        self, workspace_id: str, audience_session_id: str
    ) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM concierge_conversation_messages
            WHERE workspace_id=? AND audience_session_id=?
            ORDER BY created_at ASC
            """,
            (workspace_id, audience_session_id),
        )
        return [
            {
                "id": r["id"],
                "role": r["role"],
                "body": r["body"],
                "citations": json.loads(r["citations_json"] or "[]"),
                "caseId": r["case_id"],
                "createdAt": r["created_at"],
            }
            for r in cur.fetchall()
        ]

    @staticmethod
    def _map_case(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "workspaceId": str(row["workspace_id"]),
            "personaId": str(row["persona_id"]),
            "conciergeProfileId": row["concierge_profile_id"],
            "audienceSessionId": row["audience_session_id"],
            "identityId": row["identity_id"],
            "contactId": row["contact_id"],
            "channel": str(row["channel"]),
            "subject": str(row["subject"]),
            "status": str(row["status"]),
            "priority": str(row["priority"]),
            "assigneeUserId": row["assignee_user_id"],
            "slaFirstResponseAt": row["sla_first_response_at"],
            "slaResolutionAt": row["sla_resolution_at"],
            "firstRespondedAt": row["first_responded_at"],
            "resolvedAt": row["resolved_at"],
            "conversationSummary": row["conversation_summary"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "scope": str(row["scope"] or SCOPE),
            "productSupportScope": PRODUCT_SUPPORT_SCOPE,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }


def get_support_case_store(path: Path | None = None) -> SupportCaseStore:
    global _store
    with _lock:
        if path is not None:
            return SupportCaseStore(path=path)
        if _store is None:
            _store = SupportCaseStore()
        return _store


def reset_support_case_store_for_tests(path: Path | None = None) -> SupportCaseStore:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = SupportCaseStore(path=path) if path else SupportCaseStore()
        return _store


__all__ = [
    "PRODUCT_SUPPORT_SCOPE",
    "SCOPE",
    "SupportCaseStore",
    "get_support_case_store",
    "reset_support_case_store_for_tests",
]
