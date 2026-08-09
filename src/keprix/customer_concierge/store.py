"""SQLite durable store for concierge_profiles (Prompt 628).

Community Edition uses local SQLite. Postgres schema is applied via Alembic 033
and optional bootstrap; the active write path for CE and tests is SQLite.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.customer_concierge.models import ConciergeProfile, ConciergeSession, MeetingType, _now

_SCHEMA = """
CREATE TABLE IF NOT EXISTS concierge_profiles (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    published INTEGER NOT NULL DEFAULT 0,
    published_at TEXT,
    persona_name TEXT,
    greeting_message TEXT,
    business_name TEXT,
    business_description TEXT,
    knowledge_source_ids TEXT NOT NULL DEFAULT '[]',
    meeting_type_ids TEXT NOT NULL DEFAULT '[]',
    channel_config TEXT NOT NULL DEFAULT '{}',
    calendar_provider TEXT,
    calendar_connected INTEGER NOT NULL DEFAULT 0,
    conferencing_provider TEXT,
    conferencing_connected INTEGER NOT NULL DEFAULT 0,
    business_hours TEXT,
    escalation_email TEXT,
    ics_fallback_ok INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, persona_id)
);

CREATE INDEX IF NOT EXISTS idx_concierge_profiles_ws
    ON concierge_profiles(workspace_id);

CREATE INDEX IF NOT EXISTS idx_concierge_profiles_published
    ON concierge_profiles(workspace_id, published);

CREATE TABLE IF NOT EXISTS concierge_widget_sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_concierge_sessions_profile
    ON concierge_widget_sessions(profile_id, active);
"""

_lock = threading.Lock()
_store: ConciergeProfileStore | None = None


def default_db_path() -> Path:
    override = (os.environ.get("KEPRIX_CONCIERGE_DB_PATH") or "").strip()
    if override:
        return Path(override)
    home = Path(os.environ.get("KEPRIX_HOME") or Path.home() / ".keprix")
    data = Path(os.environ.get("KEPRIX_DATA_DIR") or home / "data")
    return data / "customer_concierge.sqlite"


class ConciergeProfileStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or default_db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def get(self, workspace_id: str, persona_id: str) -> ConciergeProfile | None:
        cur = self._conn.execute(
            "SELECT * FROM concierge_profiles WHERE workspace_id=? AND persona_id=?",
            (workspace_id, persona_id),
        )
        row = cur.fetchone()
        return ConciergeProfile.from_row(dict(row)) if row else None

    def get_by_id(self, profile_id: str) -> ConciergeProfile | None:
        cur = self._conn.execute("SELECT * FROM concierge_profiles WHERE id=?", (profile_id,))
        row = cur.fetchone()
        return ConciergeProfile.from_row(dict(row)) if row else None

    def list_for_workspace(self, workspace_id: str) -> list[ConciergeProfile]:
        cur = self._conn.execute(
            "SELECT * FROM concierge_profiles WHERE workspace_id=? ORDER BY updated_at DESC",
            (workspace_id,),
        )
        return [ConciergeProfile.from_row(dict(r)) for r in cur.fetchall()]

    def upsert_step1(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        persona_name: str,
        greeting_message: str,
        business_name: str,
        business_description: str,
        escalation_email: str,
        knowledge_source_ids: list[str] | None = None,
    ) -> ConciergeProfile:
        existing = self.get(workspace_id, persona_id)
        now = _now()
        ids = list(knowledge_source_ids or [])
        if existing:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE concierge_profiles SET
                      persona_name=?, greeting_message=?, business_name=?,
                      business_description=?, escalation_email=?,
                      knowledge_source_ids=?, updated_at=?
                    WHERE workspace_id=? AND persona_id=?
                    """,
                    (
                        persona_name,
                        greeting_message,
                        business_name,
                        business_description,
                        escalation_email,
                        json.dumps(ids),
                        now,
                        workspace_id,
                        persona_id,
                    ),
                )
            return self.get(workspace_id, persona_id)  # type: ignore[return-value]

        profile_id = str(uuid4())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO concierge_profiles (
                  id, workspace_id, persona_id, published, persona_name, greeting_message,
                  business_name, business_description, knowledge_source_ids, meeting_type_ids,
                  channel_config, escalation_email, created_at, updated_at
                ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, '[]', '{}', ?, ?, ?)
                """,
                (
                    profile_id,
                    workspace_id,
                    persona_id,
                    persona_name,
                    greeting_message,
                    business_name,
                    business_description,
                    json.dumps(ids),
                    escalation_email,
                    now,
                    now,
                ),
            )
        return self.get(workspace_id, persona_id)  # type: ignore[return-value]

    def upsert_step2(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        channels: dict[str, Any],
        business_hours: dict[str, Any],
        calendar_provider: str | None = None,
        conferencing_provider: str | None = None,
        calendar_connected: bool = False,
        conferencing_connected: bool = False,
        meeting_types: list[dict[str, Any]] | None = None,
        ics_fallback_ok: bool = True,
    ) -> ConciergeProfile:
        existing = self.get(workspace_id, persona_id)
        if not existing:
            raise ValueError("Complete step 1 before step 2")

        mts = [MeetingType.from_dict(m) for m in (meeting_types or []) if str(m.get("name") or "").strip()]
        channel_config = dict(channels or {})
        channel_config["meetingTypes"] = [m.to_dict() for m in mts]
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                UPDATE concierge_profiles SET
                  channel_config=?, business_hours=?,
                  calendar_provider=?, calendar_connected=?,
                  conferencing_provider=?, conferencing_connected=?,
                  meeting_type_ids=?, ics_fallback_ok=?, updated_at=?
                WHERE workspace_id=? AND persona_id=?
                """,
                (
                    json.dumps(channel_config),
                    json.dumps(business_hours),
                    calendar_provider,
                    1 if calendar_connected else 0,
                    conferencing_provider,
                    1 if conferencing_connected else 0,
                    json.dumps([m.id for m in mts]),
                    1 if ics_fallback_ok else 0,
                    now,
                    workspace_id,
                    persona_id,
                ),
            )
        return self.get(workspace_id, persona_id)  # type: ignore[return-value]

    def set_published(self, workspace_id: str, persona_id: str, published: bool) -> ConciergeProfile:
        existing = self.get(workspace_id, persona_id)
        if not existing:
            raise ValueError("Concierge profile not found")
        now = _now()
        published_at = existing.published_at or now if published else existing.published_at
        with self._conn:
            self._conn.execute(
                """
                UPDATE concierge_profiles SET
                  published=?, published_at=?, updated_at=?
                WHERE workspace_id=? AND persona_id=?
                """,
                (1 if published else 0, published_at, now, workspace_id, persona_id),
            )
        return self.get(workspace_id, persona_id)  # type: ignore[return-value]

    def update_connection_flags(
        self,
        workspace_id: str,
        persona_id: str,
        *,
        calendar_connected: bool,
        conferencing_connected: bool,
    ) -> ConciergeProfile | None:
        existing = self.get(workspace_id, persona_id)
        if not existing:
            return None
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                UPDATE concierge_profiles SET
                  calendar_connected=?, conferencing_connected=?, updated_at=?
                WHERE workspace_id=? AND persona_id=?
                """,
                (
                    1 if calendar_connected else 0,
                    1 if conferencing_connected else 0,
                    now,
                    workspace_id,
                    persona_id,
                ),
            )
        return self.get(workspace_id, persona_id)

    def open_session(self, profile: ConciergeProfile) -> ConciergeSession:
        if not profile.published:
            raise PermissionError("concierge_unpublished")
        sid = str(uuid4())
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO concierge_widget_sessions
                  (id, workspace_id, persona_id, profile_id, active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (sid, profile.workspace_id, profile.persona_id, profile.id, now),
            )
        return ConciergeSession(
            id=sid,
            workspace_id=profile.workspace_id,
            persona_id=profile.persona_id,
            profile_id=profile.id,
            active=True,
            created_at=now,
        )

    def get_session(self, session_id: str) -> ConciergeSession | None:
        cur = self._conn.execute(
            "SELECT * FROM concierge_widget_sessions WHERE id=?",
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        return ConciergeSession(
            id=str(d["id"]),
            workspace_id=str(d["workspace_id"]),
            persona_id=str(d["persona_id"]),
            profile_id=str(d["profile_id"]),
            active=bool(d["active"]),
            created_at=str(d["created_at"]),
            closed_at=d.get("closed_at"),
        )

    def allow_widget_message(self, session_id: str) -> bool:
        """New sessions require published; existing sessions survive unpublish."""
        session = self.get_session(session_id)
        if not session or not session.active:
            return False
        profile = self.get_by_id(session.profile_id)
        if not profile:
            return False
        if profile.published:
            return True
        # Unpublished: preserve existing conversations only
        return True


def get_concierge_store(path: Path | None = None) -> ConciergeProfileStore:
    global _store
    with _lock:
        if path is not None:
            return ConciergeProfileStore(path=path)
        if _store is None:
            _store = ConciergeProfileStore()
        return _store


def reset_concierge_store_for_tests(path: Path | None = None) -> ConciergeProfileStore:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = ConciergeProfileStore(path=path) if path else ConciergeProfileStore()
        return _store
