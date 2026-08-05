"""Pending / approved / denied / revoked remote client approvals."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from keprix.auth.config import data_dir
from keprix.security.client_approval.fingerprint import ClientFingerprint

ClientStatus = Literal["pending", "approved", "denied", "revoked", "expired"]

DEFAULT_APPROVAL_DAYS = 30

_SCHEMA = """
CREATE TABLE IF NOT EXISTS client_approvals (
    fingerprint TEXT NOT NULL,
    token_id TEXT NOT NULL,
    status TEXT NOT NULL,
    client_kind TEXT NOT NULL DEFAULT 'api',
    agent_label TEXT NOT NULL DEFAULT '',
    user_agent_summary TEXT NOT NULL DEFAULT '',
    ip_hash TEXT NOT NULL DEFAULT '',
    requested_scopes TEXT NOT NULL DEFAULT '[]',
    workspace_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expires_at TEXT,
    decided_by TEXT,
    note TEXT,
    PRIMARY KEY (fingerprint, token_id)
);
CREATE INDEX IF NOT EXISTS ix_client_approvals_status ON client_approvals(status);
CREATE INDEX IF NOT EXISTS ix_client_approvals_token ON client_approvals(token_id);
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


@dataclass
class ClientApproval:
    fingerprint: str
    token_id: str
    status: ClientStatus
    client_kind: str
    agent_label: str
    user_agent_summary: str
    ip_hash: str
    requested_scopes: list[str]
    workspace_id: str | None
    created_at: str
    updated_at: str
    last_seen_at: str
    expires_at: str | None
    decided_by: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "token_id": self.token_id,
            "status": self.status,
            "client_kind": self.client_kind,
            "agent_label": self.agent_label,
            "user_agent_summary": self.user_agent_summary,
            "ip_hash": self.ip_hash,
            "requested_scopes": list(self.requested_scopes),
            "workspace_id": self.workspace_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_seen_at": self.last_seen_at,
            "expires_at": self.expires_at,
            "decided_by": self.decided_by,
            "note": self.note,
        }

    def is_active(self, now: datetime | None = None) -> bool:
        if self.status != "approved":
            return False
        if not self.expires_at:
            return True
        try:
            exp = datetime.fromisoformat(self.expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            return exp > (now or _utcnow())
        except Exception:
            return False


class ClientApprovalStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._path = sqlite_path or Path(data_dir()) / "client_approvals.db"
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        if not self._ready:
            conn.executescript(_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    def _row_to_approval(self, row: sqlite3.Row) -> ClientApproval:
        try:
            scopes = json.loads(row["requested_scopes"] or "[]")
        except Exception:
            scopes = []
        return ClientApproval(
            fingerprint=row["fingerprint"],
            token_id=row["token_id"],
            status=row["status"],  # type: ignore[arg-type]
            client_kind=row["client_kind"] or "api",
            agent_label=row["agent_label"] or "",
            user_agent_summary=row["user_agent_summary"] or "",
            ip_hash=row["ip_hash"] or "",
            requested_scopes=[str(s) for s in scopes],
            workspace_id=row["workspace_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_seen_at=row["last_seen_at"],
            expires_at=row["expires_at"],
            decided_by=row["decided_by"],
            note=row["note"],
        )

    def get(self, fingerprint: str, token_id: str) -> ClientApproval | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM client_approvals WHERE fingerprint = ? AND token_id = ?",
                (fingerprint, token_id),
            ).fetchone()
        return self._row_to_approval(row) if row else None

    def upsert_seen(
        self,
        fp: ClientFingerprint,
        *,
        token_id: str,
        workspace_id: str | None = None,
        requested_scopes: list[str] | None = None,
        approval_days: int = DEFAULT_APPROVAL_DAYS,
    ) -> ClientApproval:
        existing = self.get(fp.fingerprint, token_id)
        now = _iso()
        if existing:
            # Touch last_seen; expire approved rows past expiry.
            status = existing.status
            if existing.status == "approved" and not existing.is_active():
                status = "expired"
            with self._conn() as conn:
                conn.execute(
                    """
                    UPDATE client_approvals SET
                        last_seen_at = ?,
                        updated_at = ?,
                        status = ?,
                        user_agent_summary = ?,
                        ip_hash = ?,
                        agent_label = ?
                    WHERE fingerprint = ? AND token_id = ?
                    """,
                    (
                        now,
                        now,
                        status,
                        fp.user_agent_summary,
                        fp.ip_hash,
                        fp.agent_label,
                        fp.fingerprint,
                        token_id,
                    ),
                )
                conn.commit()
            return self.get(fp.fingerprint, token_id) or existing

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO client_approvals (
                    fingerprint, token_id, status, client_kind, agent_label,
                    user_agent_summary, ip_hash, requested_scopes, workspace_id,
                    created_at, updated_at, last_seen_at, expires_at, decided_by, note
                ) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
                """,
                (
                    fp.fingerprint,
                    token_id,
                    fp.client_kind,
                    fp.agent_label,
                    fp.user_agent_summary,
                    fp.ip_hash,
                    json.dumps(list(requested_scopes or [])),
                    workspace_id,
                    now,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get(fp.fingerprint, token_id)  # type: ignore[return-value]

    def decide(
        self,
        fingerprint: str,
        token_id: str,
        *,
        status: ClientStatus,
        decided_by: str | None = None,
        note: str | None = None,
        approval_days: int = DEFAULT_APPROVAL_DAYS,
    ) -> ClientApproval | None:
        if status not in {"approved", "denied", "revoked"}:
            raise ValueError("status must be approved, denied, or revoked")
        existing = self.get(fingerprint, token_id)
        if existing is None:
            return None
        now = _utcnow()
        expires = None
        if status == "approved":
            expires = _iso(now + timedelta(days=max(1, int(approval_days))))
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE client_approvals SET
                    status = ?, updated_at = ?, expires_at = ?, decided_by = ?, note = ?
                WHERE fingerprint = ? AND token_id = ?
                """,
                (status, _iso(now), expires, decided_by, note, fingerprint, token_id),
            )
            conn.commit()
        return self.get(fingerprint, token_id)

    def list(
        self,
        *,
        status: ClientStatus | None = None,
        token_id: str | None = None,
        limit: int = 100,
    ) -> list[ClientApproval]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if token_id:
            clauses.append("token_id = ?")
            params.append(token_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(int(limit), 500)))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM client_approvals
                {where}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_approval(row) for row in rows]


_store: ClientApprovalStore | None = None


def get_client_approval_store() -> ClientApprovalStore:
    global _store
    if _store is None:
        _store = ClientApprovalStore()
    return _store


def reset_client_approval_store_for_tests(store: ClientApprovalStore | None = None) -> ClientApprovalStore:
    global _store
    _store = store if store is not None else ClientApprovalStore()
    return _store
