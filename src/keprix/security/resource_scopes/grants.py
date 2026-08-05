"""Persistent resource grants for agents, tokens, users, and workspaces."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from keprix.auth.config import data_dir

ActorType = Literal["agent", "api_token", "user", "workspace", "product"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS resource_acl_grants (
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    service TEXT NOT NULL,
    kind TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    actions TEXT NOT NULL DEFAULT '["read","write"]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (actor_type, actor_id, service, kind, resource_id)
);
CREATE INDEX IF NOT EXISTS ix_resource_acl_actor
    ON resource_acl_grants(actor_type, actor_id);
CREATE TABLE IF NOT EXISTS resource_acl_broad_grants (
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    service TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (actor_type, actor_id, service)
);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ResourceGrant:
    actor_type: ActorType
    actor_id: str
    service: str
    kind: str
    resource_id: str
    actions: list[str] = field(default_factory=lambda: ["read", "write"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "service": self.service,
            "kind": self.kind,
            "resource_id": self.resource_id,
            "actions": list(self.actions),
        }


class ResourceGrantStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._path = sqlite_path or Path(data_dir()) / "resource_acl_grants.db"
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

    def list_grants(self, actor_type: ActorType, actor_id: str) -> list[ResourceGrant]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM resource_acl_grants
                WHERE actor_type = ? AND actor_id = ?
                ORDER BY service, kind, resource_id
                """,
                (actor_type, actor_id),
            ).fetchall()
        out: list[ResourceGrant] = []
        for row in rows:
            try:
                actions = json.loads(row["actions"] or "[]")
            except Exception:
                actions = ["read", "write"]
            out.append(
                ResourceGrant(
                    actor_type=row["actor_type"],  # type: ignore[arg-type]
                    actor_id=row["actor_id"],
                    service=row["service"],
                    kind=row["kind"],
                    resource_id=row["resource_id"],
                    actions=[str(a) for a in actions],
                )
            )
        return out

    def service_resources(self, actor_type: ActorType, actor_id: str) -> dict[str, dict[str, list[str]]]:
        """Shape: {service: {kind: [ids]}} for enforcement."""
        grouped: dict[str, dict[str, list[str]]] = {}
        for grant in self.list_grants(actor_type, actor_id):
            grouped.setdefault(grant.service, {}).setdefault(grant.kind, [])
            if grant.resource_id not in grouped[grant.service][grant.kind]:
                grouped[grant.service][grant.kind].append(grant.resource_id)
        return grouped

    def upsert_grant(self, grant: ResourceGrant) -> ResourceGrant:
        now = _utcnow()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO resource_acl_grants (
                    actor_type, actor_id, service, kind, resource_id, actions, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(actor_type, actor_id, service, kind, resource_id) DO UPDATE SET
                    actions = excluded.actions,
                    updated_at = excluded.updated_at
                """,
                (
                    grant.actor_type,
                    grant.actor_id,
                    grant.service.lower(),
                    grant.kind,
                    grant.resource_id,
                    json.dumps(list(grant.actions)),
                    now,
                    now,
                ),
            )
            # Narrowing a broad grant: keep broad row visible but mark note.
            conn.execute(
                """
                UPDATE resource_acl_broad_grants
                SET note = COALESCE(note, '') || ' [narrowed by exact grants]'
                WHERE actor_type = ? AND actor_id = ? AND service = ?
                """,
                (grant.actor_type, grant.actor_id, grant.service.lower()),
            )
            conn.commit()
        return grant

    def revoke_grant(
        self,
        actor_type: ActorType,
        actor_id: str,
        service: str,
        kind: str,
        resource_id: str,
    ) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                """
                DELETE FROM resource_acl_grants
                WHERE actor_type = ? AND actor_id = ? AND service = ? AND kind = ? AND resource_id = ?
                """,
                (actor_type, actor_id, service.lower(), kind, resource_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_broad_grants(self, actor_type: ActorType, actor_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM resource_acl_broad_grants
                WHERE actor_type = ? AND actor_id = ?
                """,
                (actor_type, actor_id),
            ).fetchall()
        return [
            {
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "service": row["service"],
                "note": row["note"],
                "created_at": row["created_at"],
                "status": "broad",
            }
            for row in rows
        ]

    def record_broad_grant(
        self,
        actor_type: ActorType,
        actor_id: str,
        service: str,
        *,
        note: str | None = None,
    ) -> None:
        """Legacy migration: mark that this actor previously had unrestricted service access."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO resource_acl_broad_grants (actor_type, actor_id, service, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(actor_type, actor_id, service) DO UPDATE SET
                    note = COALESCE(excluded.note, resource_acl_broad_grants.note)
                """,
                (actor_type, actor_id, service.lower(), note or "legacy broad grant", _utcnow()),
            )
            conn.commit()

    def clear_actor(self, actor_type: ActorType, actor_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM resource_acl_grants WHERE actor_type = ? AND actor_id = ?",
                (actor_type, actor_id),
            )
            conn.commit()


_store: ResourceGrantStore | None = None


def get_resource_grant_store() -> ResourceGrantStore:
    global _store
    if _store is None:
        _store = ResourceGrantStore()
    return _store


def reset_resource_grant_store_for_tests(store: ResourceGrantStore | None = None) -> ResourceGrantStore:
    global _store
    _store = store if store is not None else ResourceGrantStore()
    return _store
