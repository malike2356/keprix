"""SQLite store for mutation mount proposals."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.mutation.mount.intents import MountIntent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mutation_mount_proposals (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    status TEXT NOT NULL,
    action TEXT NOT NULL,
    target_id TEXT NOT NULL,
    intent_json TEXT NOT NULL,
    proposed_by TEXT NOT NULL,
    approved_by TEXT,
    denied_by TEXT,
    deny_reason TEXT,
    trajectory_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    apply_result_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_mount_ws_status
    ON mutation_mount_proposals(workspace_id, status);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class MountProposal:
    id: str
    workspace_id: str
    status: str
    intent: MountIntent
    proposed_by: str
    approved_by: str | None = None
    denied_by: str | None = None
    deny_reason: str | None = None
    trajectory_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    apply_result: dict[str, Any] = field(default_factory=dict)

    @property
    def action(self) -> str:
        return self.intent.action

    @property
    def target_id(self) -> str:
        return self.intent.target_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "action": self.action,
            "target_id": self.target_id,
            "intent": self.intent.to_dict(),
            "proposed_by": self.proposed_by,
            "approved_by": self.approved_by,
            "denied_by": self.denied_by,
            "deny_reason": self.deny_reason,
            "trajectory_id": self.trajectory_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "apply_result": self.apply_result,
        }


class MountProposalStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        if sqlite_path is None:
            try:
                from keprix.auth.config import data_dir

                sqlite_path = Path(data_dir()) / "mutation_mount_proposals.db"
            except Exception:
                sqlite_path = Path.home() / ".keprix" / "mutation_mount_proposals.db"
        self._sqlite_path = Path(sqlite_path)
        self._lock = threading.RLock()
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._sqlite_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        if not self._ready:
            conn.executescript(_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    def create(
        self,
        *,
        intent: MountIntent,
        proposed_by: str,
        workspace_id: str = "default",
        trajectory_id: str | None = None,
        proposal_id: str | None = None,
    ) -> MountProposal:
        now = _utcnow()
        proposal = MountProposal(
            id=proposal_id or str(uuid.uuid4()),
            workspace_id=workspace_id,
            status="proposed",
            intent=intent,
            proposed_by=proposed_by,
            trajectory_id=trajectory_id,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    INSERT INTO mutation_mount_proposals (
                        id, workspace_id, status, action, target_id, intent_json,
                        proposed_by, trajectory_id, created_at, updated_at, apply_result_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        proposal.id,
                        proposal.workspace_id,
                        proposal.status,
                        proposal.action,
                        proposal.target_id,
                        json.dumps(intent.to_dict(), ensure_ascii=False),
                        proposal.proposed_by,
                        proposal.trajectory_id,
                        proposal.created_at,
                        proposal.updated_at,
                        "{}",
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return proposal

    def get(self, proposal_id: str) -> MountProposal | None:
        with self._lock:
            conn = self._conn()
            try:
                row = conn.execute(
                    "SELECT * FROM mutation_mount_proposals WHERE id = ?",
                    (proposal_id,),
                ).fetchone()
                return self._row_to_proposal(row) if row else None
            finally:
                conn.close()

    def list(
        self,
        *,
        workspace_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[MountProposal]:
        limit = max(1, min(int(limit), 200))
        clauses: list[str] = []
        params: list[Any] = []
        if workspace_id:
            clauses.append("workspace_id = ?")
            params.append(workspace_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT * FROM mutation_mount_proposals
            {where}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(sql, params).fetchall()
                return [self._row_to_proposal(r) for r in rows]
            finally:
                conn.close()

    def update(
        self,
        proposal_id: str,
        *,
        status: str | None = None,
        approved_by: str | None = None,
        denied_by: str | None = None,
        deny_reason: str | None = None,
        apply_result: dict[str, Any] | None = None,
        trajectory_id: str | None = None,
    ) -> MountProposal | None:
        current = self.get(proposal_id)
        if current is None:
            return None
        now = _utcnow()
        new_status = status or current.status
        new_approved = approved_by if approved_by is not None else current.approved_by
        new_denied = denied_by if denied_by is not None else current.denied_by
        new_reason = deny_reason if deny_reason is not None else current.deny_reason
        new_result = apply_result if apply_result is not None else current.apply_result
        new_traj = trajectory_id if trajectory_id is not None else current.trajectory_id
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    UPDATE mutation_mount_proposals SET
                        status = ?, approved_by = ?, denied_by = ?, deny_reason = ?,
                        apply_result_json = ?, trajectory_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        new_status,
                        new_approved,
                        new_denied,
                        new_reason,
                        json.dumps(new_result, ensure_ascii=False),
                        new_traj,
                        now,
                        proposal_id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return self.get(proposal_id)

    @staticmethod
    def _row_to_proposal(row: sqlite3.Row) -> MountProposal:
        intent = MountIntent.from_dict(json.loads(row["intent_json"] or "{}"))
        try:
            apply_result = json.loads(row["apply_result_json"] or "{}")
        except Exception:
            apply_result = {}
        return MountProposal(
            id=row["id"],
            workspace_id=row["workspace_id"],
            status=row["status"],
            intent=intent,
            proposed_by=row["proposed_by"],
            approved_by=row["approved_by"],
            denied_by=row["denied_by"],
            deny_reason=row["deny_reason"],
            trajectory_id=row["trajectory_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            apply_result=apply_result if isinstance(apply_result, dict) else {},
        )


_STORE: MountProposalStore | None = None
_STORE_LOCK = threading.Lock()


def get_mount_proposal_store(sqlite_path: Path | None = None) -> MountProposalStore:
    global _STORE
    if sqlite_path is not None:
        return MountProposalStore(sqlite_path=sqlite_path)
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = MountProposalStore()
        return _STORE


def reset_mount_proposal_store_for_tests(sqlite_path: Path | None = None) -> MountProposalStore:
    global _STORE
    with _STORE_LOCK:
        _STORE = MountProposalStore(sqlite_path=sqlite_path)
        return _STORE
