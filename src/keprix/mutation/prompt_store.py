"""Database-backed system prompt versioning (Prompt 152)."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.auth.config import data_dir
from keprix.database import Base, get_session_factory
from keprix.mutation.store import MutationStore, get_mutation_store

logger = logging.getLogger(__name__)

_SQLITE_PROMPT_SCHEMA = """
CREATE TABLE IF NOT EXISTS system_prompt_versions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    prompt_key TEXT NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    mutation_id TEXT,
    notes TEXT,
    UNIQUE (workspace_id, prompt_key, version)
);
CREATE INDEX IF NOT EXISTS ix_system_prompt_versions_workspace_key_active
    ON system_prompt_versions (workspace_id, prompt_key, is_active);
"""


@dataclass
class SystemPromptVersion:
    id: str
    workspace_id: str
    prompt_key: str
    version: int
    content: str
    is_active: bool
    created_at: datetime
    created_by: str
    mutation_id: str | None
    notes: str | None


class SystemPromptVersionRow(Base):
    __tablename__ = "system_prompt_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_key: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    mutation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PromptStore:
    def __init__(
        self,
        sqlite_path: Path | None = None,
        mutation_store: MutationStore | None = None,
    ) -> None:
        self._sqlite_path = sqlite_path or Path(data_dir()) / "mutation_store.db"
        self._sqlite_ready = False
        self._mutation_store = mutation_store or get_mutation_store()
        self._db_unavailable = False

    def _sqlite_conn(self) -> sqlite3.Connection:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._sqlite_path)
        if not self._sqlite_ready:
            conn.executescript(_SQLITE_PROMPT_SCHEMA)
            conn.commit()
            self._sqlite_ready = True
        return conn

    def _use_sqlite(self) -> bool:
        if self._db_unavailable:
            return True
        return get_session_factory() is None

    def get_active_prompt(self, workspace_id: str, prompt_key: str) -> str | None:
        try:
            version = self._get_active_version(workspace_id, prompt_key)
            return version.content if version is not None else None
        except Exception as exc:
            logger.warning("get_active_prompt failed: %s", exc)
            self._db_unavailable = True
            return None

    def get_active_or_default(self, workspace_id: str, prompt_key: str, default: str) -> str:
        active = self.get_active_prompt(workspace_id, prompt_key)
        return active if active is not None else default

    def stage_improvement(
        self,
        workspace_id: str,
        prompt_key: str,
        suggested_content: str,
        rationale: str,
        confidence: float,
        auto_approve_threshold: float,
    ) -> SystemPromptVersion:
        status = "approved" if confidence >= auto_approve_threshold else "staged"
        is_active = status == "approved"
        mutation_id = str(uuid.uuid4())
        before = self.get_active_prompt(workspace_id, prompt_key)
        mutation = self._mutation_store.save_mutation_event(
            record_id=mutation_id,
            workspace_id=workspace_id,
            tier="prompt",
            trigger="prompt_improver",
            status=status,
            name=prompt_key,
            description=rationale,
            before_value=before,
            after_value=suggested_content,
            approved_by="auto" if is_active else None,
            quality_score=confidence,
            metadata={"prompt_key": prompt_key, "rationale": rationale},
        )
        version = self._insert_version(
            workspace_id=workspace_id,
            prompt_key=prompt_key,
            content=suggested_content,
            created_by="mutation_improver",
            mutation_id=mutation.id,
            notes=rationale,
            is_active=is_active,
        )
        if is_active:
            self._deactivate_other_versions(workspace_id, prompt_key, keep_id=version.id)
        return version

    def activate_version(self, version_id: str, activated_by: str) -> SystemPromptVersion:
        version = self._fetch_version(version_id)
        if version is None:
            raise ValueError(f"prompt version not found: {version_id}")
        self._deactivate_other_versions(version.workspace_id, version.prompt_key, keep_id=version_id)
        self._set_version_active(version_id, True)
        if version.mutation_id:
            self._mutation_store.update_mutation_status(
                version.mutation_id,
                "approved",
                approved_by=activated_by,
            )
        restored = self._fetch_version(version_id)
        if restored is None:
            raise ValueError(f"prompt version not found after activation: {version_id}")
        return restored

    def rollback_to_previous(
        self,
        workspace_id: str,
        prompt_key: str,
        rolled_back_by: str,
    ) -> SystemPromptVersion | None:
        current = self._get_active_version(workspace_id, prompt_key)
        if current is None:
            return None
        history = self.get_history(workspace_id, prompt_key, limit=50)
        previous = None
        for item in history:
            if item.id == current.id:
                continue
            if item.version < current.version:
                previous = item
                break
        if previous is None:
            return None

        self._set_version_active(current.id, False)
        self._deactivate_other_versions(workspace_id, prompt_key, keep_id=previous.id)
        self._set_version_active(previous.id, True)

        if current.mutation_id:
            self._mutation_store.save_mutation_event(
                workspace_id=workspace_id,
                tier="prompt",
                trigger="rollback",
                status="rolled_back",
                name=prompt_key,
                description=f"Rolled back version {current.version}",
                before_value=current.content,
                after_value=previous.content,
                approved_by=rolled_back_by,
                rollback_of=current.mutation_id,
                metadata={"restored_version_id": previous.id},
            )
        return self._fetch_version(previous.id)

    def get_history(self, workspace_id: str, prompt_key: str, limit: int = 20) -> list[SystemPromptVersion]:
        rows = self._list_versions(workspace_id, prompt_key, limit=limit)
        return rows

    def list_prompt_versions(
        self,
        workspace_id: str,
        *,
        prompt_key: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[SystemPromptVersion], int]:
        page = max(1, page)
        per_page = max(1, min(per_page, 100))
        if self._use_sqlite():
            rows = self._list_all_versions_sqlite(workspace_id, prompt_key=prompt_key)
        else:
            import asyncio

            rows = asyncio.run(self._list_all_versions_postgres(workspace_id, prompt_key=prompt_key))
        total = len(rows)
        start = (page - 1) * per_page
        return rows[start : start + per_page], total

    def get_version(self, version_id: str) -> SystemPromptVersion | None:
        return self._fetch_version(version_id)

    def _next_version(self, workspace_id: str, prompt_key: str) -> int:
        history = self._list_versions(workspace_id, prompt_key, limit=1)
        if not history:
            return 1
        return history[0].version + 1

    def _insert_version(
        self,
        *,
        workspace_id: str,
        prompt_key: str,
        content: str,
        created_by: str,
        mutation_id: str | None,
        notes: str | None,
        is_active: bool,
    ) -> SystemPromptVersion:
        version_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        version_num = self._next_version(workspace_id, prompt_key)
        row = {
            "id": version_id,
            "workspace_id": workspace_id,
            "prompt_key": prompt_key,
            "version": version_num,
            "content": content,
            "is_active": 1 if is_active else 0,
            "created_at": now,
            "created_by": created_by,
            "mutation_id": mutation_id,
            "notes": notes,
        }
        if self._use_sqlite():
            self._insert_sqlite_version(row)
        else:
            self._insert_postgres_version_sync(row)
        return _row_to_version(row)

    def _get_active_version(self, workspace_id: str, prompt_key: str) -> SystemPromptVersion | None:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                cur = conn.execute(
                    """
                    SELECT * FROM system_prompt_versions
                    WHERE workspace_id = ? AND prompt_key = ? AND is_active = 1
                    ORDER BY version DESC LIMIT 1
                    """,
                    (workspace_id, prompt_key),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                columns = [part[0] for part in cur.description]
                return _row_to_version(_sqlite_row_dict(columns, row))
        import asyncio

        return asyncio.run(self._fetch_active_postgres(workspace_id, prompt_key))

    def _fetch_version(self, version_id: str) -> SystemPromptVersion | None:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                cur = conn.execute("SELECT * FROM system_prompt_versions WHERE id = ?", (version_id,))
                row = cur.fetchone()
                if row is None:
                    return None
                columns = [part[0] for part in cur.description]
                return _row_to_version(_sqlite_row_dict(columns, row))
        import asyncio

        return asyncio.run(self._fetch_version_postgres(version_id))

    def _list_versions(self, workspace_id: str, prompt_key: str, *, limit: int) -> list[SystemPromptVersion]:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                cur = conn.execute(
                    """
                    SELECT * FROM system_prompt_versions
                    WHERE workspace_id = ? AND prompt_key = ?
                    ORDER BY version DESC LIMIT ?
                    """,
                    (workspace_id, prompt_key, limit),
                )
                columns = [part[0] for part in cur.description]
                return [_row_to_version(_sqlite_row_dict(columns, row)) for row in cur.fetchall()]
        import asyncio

        return asyncio.run(self._list_versions_postgres(workspace_id, prompt_key, limit=limit))

    def _list_all_versions_sqlite(
        self,
        workspace_id: str,
        *,
        prompt_key: str | None,
    ) -> list[SystemPromptVersion]:
        query = "SELECT * FROM system_prompt_versions WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if prompt_key:
            query += " AND prompt_key = ?"
            params.append(prompt_key)
        query += " ORDER BY created_at DESC"
        with self._sqlite_conn() as conn:
            cur = conn.execute(query, params)
            columns = [part[0] for part in cur.description]
            return [_row_to_version(_sqlite_row_dict(columns, row)) for row in cur.fetchall()]

    async def _list_all_versions_postgres(
        self,
        workspace_id: str,
        *,
        prompt_key: str | None,
    ) -> list[SystemPromptVersion]:
        factory = get_session_factory()
        if factory is None:
            return self._list_all_versions_sqlite(workspace_id, prompt_key=prompt_key)
        query = select(SystemPromptVersionRow).where(SystemPromptVersionRow.workspace_id == workspace_id)
        if prompt_key:
            query = query.where(SystemPromptVersionRow.prompt_key == prompt_key)
        query = query.order_by(SystemPromptVersionRow.created_at.desc())
        async with factory() as session:
            result = await session.execute(query)
            return [_entry_to_version(entry) for entry in result.scalars().all()]

    def _deactivate_other_versions(self, workspace_id: str, prompt_key: str, *, keep_id: str) -> None:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                conn.execute(
                    """
                    UPDATE system_prompt_versions
                    SET is_active = 0
                    WHERE workspace_id = ? AND prompt_key = ? AND id != ?
                    """,
                    (workspace_id, prompt_key, keep_id),
                )
                conn.commit()
            return
        import asyncio

        asyncio.run(self._deactivate_other_postgres(workspace_id, prompt_key, keep_id=keep_id))

    def _set_version_active(self, version_id: str, active: bool) -> None:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                conn.execute(
                    "UPDATE system_prompt_versions SET is_active = ? WHERE id = ?",
                    (1 if active else 0, version_id),
                )
                conn.commit()
            return
        import asyncio

        asyncio.run(self._set_active_postgres(version_id, active))

    def _insert_sqlite_version(self, row: dict[str, Any]) -> None:
        with self._sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO system_prompt_versions (
                    id, workspace_id, prompt_key, version, content, is_active,
                    created_at, created_by, mutation_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["workspace_id"],
                    row["prompt_key"],
                    row["version"],
                    row["content"],
                    row["is_active"],
                    row["created_at"].isoformat(),
                    row["created_by"],
                    row["mutation_id"],
                    row["notes"],
                ),
            )
            conn.commit()

    def _insert_postgres_version_sync(self, row: dict[str, Any]) -> None:
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._insert_postgres_version(row))
            return
        self._insert_sqlite_version(row)

    async def _insert_postgres_version(self, row: dict[str, Any]) -> None:
        factory = get_session_factory()
        if factory is None:
            self._insert_sqlite_version(row)
            return
        entry = SystemPromptVersionRow(
            id=row["id"],
            workspace_id=row["workspace_id"],
            prompt_key=row["prompt_key"],
            version=row["version"],
            content=row["content"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            created_by=row["created_by"],
            mutation_id=row["mutation_id"],
            notes=row["notes"],
        )
        async with factory() as session:
            session.add(entry)
            await session.commit()

    async def _fetch_active_postgres(self, workspace_id: str, prompt_key: str) -> SystemPromptVersion | None:
        factory = get_session_factory()
        if factory is None:
            return self._get_active_version(workspace_id, prompt_key)
        query = (
            select(SystemPromptVersionRow)
            .where(
                SystemPromptVersionRow.workspace_id == workspace_id,
                SystemPromptVersionRow.prompt_key == prompt_key,
                SystemPromptVersionRow.is_active.is_(True),
            )
            .order_by(SystemPromptVersionRow.version.desc())
            .limit(1)
        )
        async with factory() as session:
            result = await session.execute(query)
            entry = result.scalar_one_or_none()
            return _entry_to_version(entry) if entry else None

    async def _fetch_version_postgres(self, version_id: str) -> SystemPromptVersion | None:
        factory = get_session_factory()
        if factory is None:
            return self._fetch_version(version_id)
        async with factory() as session:
            result = await session.execute(
                select(SystemPromptVersionRow).where(SystemPromptVersionRow.id == version_id)
            )
            entry = result.scalar_one_or_none()
            return _entry_to_version(entry) if entry else None

    async def _list_versions_postgres(
        self,
        workspace_id: str,
        prompt_key: str,
        *,
        limit: int,
    ) -> list[SystemPromptVersion]:
        factory = get_session_factory()
        if factory is None:
            return self._list_versions(workspace_id, prompt_key, limit=limit)
        query = (
            select(SystemPromptVersionRow)
            .where(
                SystemPromptVersionRow.workspace_id == workspace_id,
                SystemPromptVersionRow.prompt_key == prompt_key,
            )
            .order_by(SystemPromptVersionRow.version.desc())
            .limit(limit)
        )
        async with factory() as session:
            result = await session.execute(query)
            return [_entry_to_version(entry) for entry in result.scalars().all()]

    async def _deactivate_other_postgres(self, workspace_id: str, prompt_key: str, *, keep_id: str) -> None:
        factory = get_session_factory()
        if factory is None:
            self._deactivate_other_versions(workspace_id, prompt_key, keep_id=keep_id)
            return
        async with factory() as session:
            result = await session.execute(
                select(SystemPromptVersionRow).where(
                    SystemPromptVersionRow.workspace_id == workspace_id,
                    SystemPromptVersionRow.prompt_key == prompt_key,
                    SystemPromptVersionRow.id != keep_id,
                )
            )
            for entry in result.scalars().all():
                entry.is_active = False
            await session.commit()

    async def _set_active_postgres(self, version_id: str, active: bool) -> None:
        factory = get_session_factory()
        if factory is None:
            self._set_version_active(version_id, active)
            return
        async with factory() as session:
            result = await session.execute(
                select(SystemPromptVersionRow).where(SystemPromptVersionRow.id == version_id)
            )
            entry = result.scalar_one_or_none()
            if entry is None:
                return
            entry.is_active = active
            await session.commit()


_store: PromptStore | None = None


def get_prompt_store() -> PromptStore:
    global _store
    if _store is None:
        _store = PromptStore()
    return _store


def _sqlite_row_dict(columns: list[str], row: tuple[Any, ...]) -> dict[str, Any]:
    data = dict(zip(columns, row))
    created_at = data.get("created_at")
    data["created_at"] = datetime.fromisoformat(str(created_at)) if created_at else datetime.now(timezone.utc)
    data["is_active"] = bool(data.get("is_active"))
    return data


def _row_to_version(row: dict[str, Any]) -> SystemPromptVersion:
    return SystemPromptVersion(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        prompt_key=str(row["prompt_key"]),
        version=int(row["version"]),
        content=str(row["content"]),
        is_active=bool(row.get("is_active")),
        created_at=row["created_at"],
        created_by=str(row["created_by"]),
        mutation_id=row.get("mutation_id"),
        notes=row.get("notes"),
    )


def _entry_to_version(entry: SystemPromptVersionRow) -> SystemPromptVersion:
    return SystemPromptVersion(
        id=entry.id,
        workspace_id=entry.workspace_id,
        prompt_key=entry.prompt_key,
        version=entry.version,
        content=entry.content,
        is_active=entry.is_active,
        created_at=entry.created_at,
        created_by=entry.created_by,
        mutation_id=entry.mutation_id,
        notes=entry.notes,
    )
