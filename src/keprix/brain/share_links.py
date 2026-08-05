"""Read-only brain graph share links."""

from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import bcrypt

ShareScope = Literal["all", "memories_only", "skills_only"]

SCOPE_KINDS: dict[ShareScope, set[str] | None] = {
    "all": None,
    "memories_only": {"memory"},
    "skills_only": {"skill"},
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _share_db_path() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home())
    except Exception:
        root = Path.home() / ".keprix"
    root.mkdir(parents=True, exist_ok=True)
    return root / "brain_share_links.sqlite"


def _connect() -> sqlite3.Connection:
    path = _share_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS brain_share_links (
            share_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            scope TEXT NOT NULL DEFAULT 'all',
            password_hash TEXT,
            access_count INTEGER NOT NULL DEFAULT 0,
            last_accessed_at TEXT
        )
        """
    )
    return conn


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


@dataclass
class BrainShareLink:
    share_id: str
    workspace_id: str
    created_by: str
    created_at: datetime
    expires_at: datetime | None
    scope: ShareScope
    password_hash: str | None
    access_count: int
    last_accessed_at: datetime | None

    def to_dict(self, *, include_url: bool = False, base_url: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {
            "share_id": self.share_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scope": self.scope,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "password_protected": bool(self.password_hash),
        }
        if include_url:
            payload["url"] = f"{base_url.rstrip('/')}/brain/share/{self.share_id}"
        return payload

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "BrainShareLink":
        return cls(
            share_id=row["share_id"],
            workspace_id=row["workspace_id"],
            created_by=row["created_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            scope=row["scope"],
            password_hash=row["password_hash"],
            access_count=int(row["access_count"] or 0),
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"]) if row["last_accessed_at"] else None,
        )


class BrainShareLinkStore:
    def create(
        self,
        *,
        workspace_id: str,
        created_by: str,
        scope: ShareScope = "all",
        expires_in_days: int | None = 7,
        password: str | None = None,
    ) -> BrainShareLink:
        share_id = secrets.token_urlsafe(15)[:20]
        created_at = _utcnow()
        expires_at = created_at + timedelta(days=expires_in_days) if expires_in_days else None
        password_hash = _hash_password(password) if password else None
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO brain_share_links(
                    share_id, workspace_id, created_by, created_at, expires_at, scope, password_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    share_id,
                    workspace_id,
                    created_by,
                    created_at.isoformat(),
                    expires_at.isoformat() if expires_at else None,
                    scope,
                    password_hash,
                ),
            )
        return BrainShareLink(
            share_id=share_id,
            workspace_id=workspace_id,
            created_by=created_by,
            created_at=created_at,
            expires_at=expires_at,
            scope=scope,
            password_hash=password_hash,
            access_count=0,
            last_accessed_at=None,
        )

    def get(self, share_id: str) -> BrainShareLink | None:
        with _connect() as conn:
            row = conn.execute("SELECT * FROM brain_share_links WHERE share_id = ?", (share_id,)).fetchone()
        return BrainShareLink.from_row(row) if row else None

    def list_for_workspace(self, workspace_id: str) -> list[BrainShareLink]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM brain_share_links WHERE workspace_id = ? ORDER BY created_at DESC",
                (workspace_id,),
            ).fetchall()
        return [BrainShareLink.from_row(row) for row in rows]

    def revoke(self, share_id: str, workspace_id: str) -> bool:
        with _connect() as conn:
            cursor = conn.execute(
                "DELETE FROM brain_share_links WHERE share_id = ? AND workspace_id = ?",
                (share_id, workspace_id),
            )
            return int(cursor.rowcount or 0) > 0

    def record_access(self, share_id: str) -> None:
        now = _utcnow().isoformat()
        with _connect() as conn:
            conn.execute(
                """
                UPDATE brain_share_links
                SET access_count = access_count + 1, last_accessed_at = ?
                WHERE share_id = ?
                """,
                (now, share_id),
            )

    def verify_password(self, link: BrainShareLink, password: str | None) -> bool:
        if not link.password_hash:
            return True
        if not password:
            return False
        return _verify_password(password, link.password_hash)

    def is_expired(self, link: BrainShareLink) -> bool:
        if link.expires_at is None:
            return False
        return _utcnow() >= link.expires_at


share_link_store = BrainShareLinkStore()
