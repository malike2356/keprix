"""Persistence for mutation_events (Prompt 150)."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.auth.config import data_dir
from keprix.database import Base, get_session_factory
from keprix.mutation.config import get_mutation_settings

logger = logging.getLogger(__name__)

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS mutation_events (
    id TEXT PRIMARY KEY,
    recorded_at TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    trigger TEXT NOT NULL,
    status TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    source_code TEXT,
    before_value TEXT,
    after_value TEXT,
    approved_by TEXT,
    approved_at TEXT,
    quality_score REAL,
    use_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TEXT,
    rollback_of TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_mutation_events_workspace_status
    ON mutation_events(workspace_id, status);
CREATE INDEX IF NOT EXISTS ix_mutation_events_tier_name
    ON mutation_events(tier, name);
CREATE TABLE IF NOT EXISTS mutation_quality_samples (
    id TEXT PRIMARY KEY,
    mutation_id TEXT NOT NULL,
    sampled_at TEXT NOT NULL,
    task_id TEXT,
    run_id TEXT,
    outcome TEXT NOT NULL,
    score REAL,
    feedback TEXT
);
CREATE INDEX IF NOT EXISTS ix_mutation_quality_mutation_id
    ON mutation_quality_samples(mutation_id);
"""


@dataclass
class MutationRecord:
    id: str
    recorded_at: datetime
    workspace_id: str
    tier: str
    trigger: str
    status: str
    name: str
    description: str | None
    source_code: str | None
    before_value: str | None
    after_value: str | None
    approved_by: str | None
    approved_at: datetime | None
    quality_score: float | None
    use_count: int
    last_used_at: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)


class MutationEventRow(Base):
    __tablename__ = "mutation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(Text, nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class MutationQualitySampleRow(Base):
    __tablename__ = "mutation_quality_samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mutation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    task_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)


class MutationStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._sqlite_path = sqlite_path or Path(data_dir()) / "mutation_store.db"
        self._sqlite_ready = False

    def _sqlite_conn(self) -> sqlite3.Connection:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._sqlite_path)
        if not self._sqlite_ready:
            conn.executescript(_SQLITE_SCHEMA)
            conn.commit()
            self._sqlite_ready = True
        return conn

    def _use_sqlite(self) -> bool:
        return get_session_factory() is None

    def save_generated_tool(
        self,
        workspace_id: str,
        tool_name: str,
        description: str,
        source_code: str,
        trigger: str,
        confidence: float,
        auto_approve_threshold: float,
    ) -> MutationRecord:
        status = "approved" if confidence >= auto_approve_threshold else "staged"
        now = datetime.now(timezone.utc)
        record_id = str(uuid.uuid4())
        row = {
            "id": record_id,
            "recorded_at": now,
            "workspace_id": workspace_id,
            "tier": "tool",
            "trigger": trigger,
            "status": status,
            "name": tool_name,
            "description": description,
            "source_code": source_code,
            "before_value": None,
            "after_value": None,
            "approved_by": "auto" if status == "approved" else None,
            "approved_at": now if status == "approved" else None,
            "quality_score": confidence,
            "use_count": 0,
            "last_used_at": None,
            "rollback_of": None,
            "metadata": {"confidence": confidence},
        }
        if self._use_sqlite():
            self._insert_sqlite(row)
        else:
            self._insert_postgres_sync(row)
        return _row_to_record(row)

    def save_mutation_event(
        self,
        *,
        workspace_id: str,
        tier: str,
        trigger: str,
        status: str,
        name: str,
        description: str | None = None,
        source_code: str | None = None,
        before_value: str | None = None,
        after_value: str | None = None,
        approved_by: str | None = None,
        quality_score: float | None = None,
        rollback_of: str | None = None,
        metadata: dict[str, Any] | None = None,
        record_id: str | None = None,
    ) -> MutationRecord:
        now = datetime.now(timezone.utc)
        row = {
            "id": record_id or str(uuid.uuid4()),
            "recorded_at": now,
            "workspace_id": workspace_id,
            "tier": tier,
            "trigger": trigger,
            "status": status,
            "name": name,
            "description": description,
            "source_code": source_code,
            "before_value": before_value,
            "after_value": after_value,
            "approved_by": approved_by,
            "approved_at": now if status == "approved" else None,
            "quality_score": quality_score,
            "use_count": 0,
            "last_used_at": None,
            "rollback_of": rollback_of,
            "metadata": metadata or {},
        }
        if self._use_sqlite():
            self._insert_sqlite(row)
        else:
            self._insert_postgres_sync(row)
        return _row_to_record(row)

    def update_mutation_status(
        self,
        mutation_id: str,
        status: str,
        *,
        approved_by: str | None = None,
    ) -> MutationRecord | None:
        return self.update_status(mutation_id, status, approved_by=approved_by)

    def _insert_postgres_sync(self, row: dict[str, Any]) -> None:
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._insert_postgres(row))
            return
        self._insert_sqlite(row)

    def get_generated_tool(self, record_id: str) -> MutationRecord | None:
        if self._use_sqlite():
            row = self._fetch_sqlite(record_id)
            return _row_to_record(row) if row else None
        import asyncio

        return asyncio.run(self._fetch_postgres(record_id))

    def list_generated_tools(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
    ) -> list[MutationRecord]:
        if self._use_sqlite():
            rows = self._list_sqlite(workspace_id, status=status)
            return [_row_to_record(row) for row in rows]
        import asyncio

        return asyncio.run(self._list_postgres(workspace_id, status=status))

    def update_status(
        self,
        record_id: str,
        status: str,
        *,
        approved_by: str | None = None,
    ) -> MutationRecord | None:
        now = datetime.now(timezone.utc)
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                conn.execute(
                    "UPDATE mutation_events SET status = ?, approved_by = ?, approved_at = ? WHERE id = ?",
                    (status, approved_by, now.isoformat() if status == "approved" else None, record_id),
                )
                conn.commit()
            row = self._fetch_sqlite(record_id)
            return _row_to_record(row) if row else None
        import asyncio

        return asyncio.run(self._update_status_postgres(record_id, status, approved_by=approved_by))

    def write_tool_to_disk(self, record: MutationRecord, generated_dir: Path) -> Path:
        if record.status not in {"approved", "installed"}:
            raise ValueError("only approved tool records can be written to disk")
        if not record.source_code:
            raise ValueError("record has no source_code")
        generated_dir.mkdir(parents=True, exist_ok=True)
        final_path = generated_dir / f"{record.name}.py"
        tmp_path = generated_dir / f".{record.name}.py.tmp"
        tmp_path.write_text(record.source_code, encoding="utf-8")
        tmp_path.replace(final_path)
        try:
            from keprix.agent.keprix.tool_signer import sign_tool

            metadata = {"record_id": record.id, "description": record.description or ""}
            signature = sign_tool(record.name, record.source_code, metadata)
            final_path.with_name(f"{record.name}.sig").write_text(signature, encoding="utf-8")
            final_path.with_name(f"{record.name}.meta.json").write_text(
                json.dumps(metadata),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("could not sign generated tool %s: %s", record.name, exc)
        return final_path

    def load_tools_on_startup(self, workspace_id: str, generated_dir: Path) -> int:
        records = self.list_generated_tools(workspace_id, status="approved")
        written = 0
        for record in records:
            try:
                self.write_tool_to_disk(record, generated_dir)
                written += 1
            except Exception as exc:
                logger.warning("failed to write generated tool %s on startup: %s", record.name, exc)
        return self.reload_registry(generated_dir)

    async def list_generated_tools_async(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
    ) -> list[MutationRecord]:
        if self._use_sqlite():
            rows = self._list_sqlite(workspace_id, status=status)
            return [_row_to_record(row) for row in rows]
        return await self._list_postgres(workspace_id, status=status)

    async def load_tools_on_startup_async(self, workspace_id: str, generated_dir: Path) -> int:
        records = await self.list_generated_tools_async(workspace_id, status="approved")
        for record in records:
            try:
                self.write_tool_to_disk(record, generated_dir)
            except Exception as exc:
                logger.warning("failed to write generated tool %s on startup: %s", record.name, exc)
        return self.reload_registry(generated_dir)

    async def ensure_mutation_tables(self) -> None:
        from keprix.database import get_engine
        engine = get_engine()
        if engine is None:
            return
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: MutationEventRow.__table__.create(sync_conn, checkfirst=True)
            )
            await conn.run_sync(
                lambda sync_conn: MutationQualitySampleRow.__table__.create(sync_conn, checkfirst=True)
            )

    def reload_registry(self, generated_dir: Path) -> int:
        try:
            from tools.registry import registry

            imported = registry.reload_generated_tools(generated_dir)
            logger.info("Reloaded %d generated tools from %s", imported, generated_dir)
            return imported
        except Exception as exc:
            logger.warning("registry reload failed: %s", exc)
            return 0

    def generated_tools_dir(self) -> Path:
        return Path(get_mutation_settings().generated_tools_dir)

    def find_generated_by_name(
        self,
        workspace_id: str,
        tool_name: str,
        *,
        statuses: tuple[str, ...] = ("staged", "approved", "installed"),
    ) -> MutationRecord | None:
        normalized = tool_name.strip().lower()
        for record in self.list_generated_tools(workspace_id):
            if record.name.strip().lower() == normalized and record.status in statuses:
                return record
        return None

    def list_mutations(
        self,
        workspace_id: str,
        *,
        tier: str | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[MutationRecord], int]:
        page = max(1, page)
        per_page = max(1, min(per_page, 100))
        if self._use_sqlite():
            rows = self._list_mutations_sqlite(workspace_id, tier=tier, status=status)
        else:
            import asyncio

            rows = asyncio.run(self._list_mutations_postgres(workspace_id, tier=tier, status=status))
        total = len(rows)
        start = (page - 1) * per_page
        page_rows = rows[start : start + per_page]
        return [_row_to_record(row) for row in page_rows], total

    def find_approved_mutation_by_name(
        self,
        workspace_id: str,
        tool_name: str,
        *,
        tier: str = "tool",
    ) -> MutationRecord | None:
        records, _total = self.list_mutations(workspace_id, tier=tier, status="approved", page=1, per_page=500)
        normalized = tool_name.strip().lower()
        for record in records:
            if record.name.strip().lower() == normalized:
                return record
        return None

    def find_active_prompt_mutation(self, workspace_id: str, prompt_key: str) -> MutationRecord | None:
        records, _total = self.list_mutations(workspace_id, tier="prompt", page=1, per_page=500)
        key = prompt_key.strip().lower()
        active = [
            record
            for record in records
            if record.name.strip().lower() == key and record.status in {"approved", "staged"}
        ]
        if not active:
            return None
        active.sort(key=lambda row: row.recorded_at, reverse=True)
        return active[0]

    def update_mutation_usage(
        self,
        mutation_id: str,
        *,
        quality_score: float,
        use_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> MutationRecord | None:
        now = datetime.now(timezone.utc)
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                if metadata is not None:
                    conn.execute(
                        """
                        UPDATE mutation_events
                        SET quality_score = ?, use_count = ?, last_used_at = ?, metadata = ?
                        WHERE id = ?
                        """,
                        (quality_score, use_count, now.isoformat(), json.dumps(metadata), mutation_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE mutation_events
                        SET quality_score = ?, use_count = ?, last_used_at = ?
                        WHERE id = ?
                        """,
                        (quality_score, use_count, now.isoformat(), mutation_id),
                    )
                conn.commit()
            row = self._fetch_sqlite(mutation_id)
            return _row_to_record(row) if row else None
        import asyncio

        return asyncio.run(
            self._update_usage_postgres(
                mutation_id,
                quality_score=quality_score,
                use_count=use_count,
                metadata=metadata,
            )
        )

    def insert_quality_sample(
        self,
        *,
        mutation_id: str,
        outcome: str,
        score: float,
        run_id: str | None = None,
        task_id: str | None = None,
        feedback: str | None = None,
    ) -> str:
        sample_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        row = {
            "id": sample_id,
            "mutation_id": mutation_id,
            "sampled_at": now,
            "task_id": task_id,
            "run_id": run_id,
            "outcome": outcome,
            "score": score,
            "feedback": feedback,
        }
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO mutation_quality_samples (
                        id, mutation_id, sampled_at, task_id, run_id, outcome, score, feedback
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["mutation_id"],
                        row["sampled_at"].isoformat(),
                        row["task_id"],
                        row["run_id"],
                        row["outcome"],
                        row["score"],
                        row["feedback"],
                    ),
                )
                conn.commit()
            return sample_id
        import asyncio

        asyncio.run(self._insert_quality_sample_postgres(row))
        return sample_id

    def get_quality_samples(self, mutation_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                cur = conn.execute(
                    """
                    SELECT * FROM mutation_quality_samples
                    WHERE mutation_id = ?
                    ORDER BY sampled_at DESC
                    LIMIT ?
                    """,
                    (mutation_id, limit),
                )
                columns = [part[0] for part in cur.description]
                return [_quality_sample_dict(columns, row) for row in cur.fetchall()]
        import asyncio

        return asyncio.run(self._get_quality_samples_postgres(mutation_id, limit=limit))

    def clear_source_code(self, mutation_id: str) -> None:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                conn.execute("UPDATE mutation_events SET source_code = NULL WHERE id = ?", (mutation_id,))
                conn.commit()
            return
        import asyncio

        asyncio.run(self._clear_source_code_postgres(mutation_id))

    def quarantine_tool_mutation(self, record: MutationRecord) -> None:
        generated_dir = self.generated_tools_dir()
        for suffix in (".py", ".sig", ".meta.json"):
            path = generated_dir / f"{record.name}{suffix}"
            if path.exists():
                try:
                    path.unlink()
                except OSError as exc:
                    logger.warning("could not delete %s during quarantine: %s", path, exc)
        try:
            from tools.registry import registry

            registry.deregister_tool(record.name)
        except Exception as exc:
            logger.warning("could not deregister quarantined tool %s: %s", record.name, exc)
        metadata = dict(record.metadata)
        metadata["quarantined"] = True
        self._set_status_and_metadata(record.id, "quarantined", metadata)

    async def _update_usage_postgres(
        self,
        mutation_id: str,
        *,
        quality_score: float,
        use_count: int,
        metadata: dict[str, Any] | None,
    ) -> MutationRecord | None:
        factory = get_session_factory()
        if factory is None:
            return self.update_mutation_usage(
                mutation_id,
                quality_score=quality_score,
                use_count=use_count,
                metadata=metadata,
            )
        async with factory() as session:
            result = await session.execute(select(MutationEventRow).where(MutationEventRow.id == mutation_id))
            entry = result.scalar_one_or_none()
            if entry is None:
                return None
            entry.quality_score = quality_score
            entry.use_count = use_count
            entry.last_used_at = datetime.now(timezone.utc)
            if metadata is not None:
                entry.metadata_json = metadata
            await session.commit()
            return _entry_to_record(entry)

    async def _insert_quality_sample_postgres(self, row: dict[str, Any]) -> None:
        factory = get_session_factory()
        if factory is None:
            self.insert_quality_sample(
                mutation_id=row["mutation_id"],
                outcome=row["outcome"],
                score=float(row["score"]),
                run_id=row.get("run_id"),
                task_id=row.get("task_id"),
                feedback=row.get("feedback"),
            )
            return
        entry = MutationQualitySampleRow(
            id=row["id"],
            mutation_id=row["mutation_id"],
            sampled_at=row["sampled_at"],
            task_id=row.get("task_id"),
            run_id=row.get("run_id"),
            outcome=row["outcome"],
            score=row.get("score"),
            feedback=row.get("feedback"),
        )
        async with factory() as session:
            session.add(entry)
            await session.commit()

    async def _get_quality_samples_postgres(self, mutation_id: str, *, limit: int) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            return self.get_quality_samples(mutation_id, limit=limit)
        query = (
            select(MutationQualitySampleRow)
            .where(MutationQualitySampleRow.mutation_id == mutation_id)
            .order_by(MutationQualitySampleRow.sampled_at.desc())
            .limit(limit)
        )
        async with factory() as session:
            result = await session.execute(query)
            rows = []
            for entry in result.scalars().all():
                rows.append(
                    {
                        "id": entry.id,
                        "mutation_id": entry.mutation_id,
                        "sampled_at": entry.sampled_at,
                        "task_id": entry.task_id,
                        "run_id": entry.run_id,
                        "outcome": entry.outcome,
                        "score": entry.score,
                        "feedback": entry.feedback,
                    }
                )
            return rows

    async def _clear_source_code_postgres(self, mutation_id: str) -> None:
        factory = get_session_factory()
        if factory is None:
            self.clear_source_code(mutation_id)
            return
        async with factory() as session:
            result = await session.execute(select(MutationEventRow).where(MutationEventRow.id == mutation_id))
            entry = result.scalar_one_or_none()
            if entry is None:
                return
            entry.source_code = None
            await session.commit()

    def mutation_stats(self, workspace_id: str) -> dict[str, Any]:
        if self._use_sqlite():
            rows = self._list_mutations_sqlite(workspace_id)
        else:
            import asyncio

            rows = asyncio.run(self._list_mutations_postgres(workspace_id))
        counts: dict[str, dict[str, int]] = {}
        for row in rows:
            tier = str(row["tier"])
            status = str(row["status"])
            counts.setdefault(tier, {})
            counts[tier][status] = counts[tier].get(status, 0) + 1
        return {"counts": counts, "total": len(rows)}

    def approve_mutation(self, mutation_id: str, approved_by: str) -> MutationRecord | None:
        record = self.get_generated_tool(mutation_id)
        if record is None:
            return None
        if record.tier == "code":
            try:
                self._approve_code_mutation(record, approved_by)
            except ValueError as exc:
                logger.warning("code mutation approve failed: %s", exc)
                return None
            return self.get_generated_tool(mutation_id)
        record = self.update_status(mutation_id, "approved", approved_by=approved_by)
        if record is None:
            return None
        if record.tier == "tool" and record.source_code:
            generated_dir = self.generated_tools_dir()
            self.write_tool_to_disk(record, generated_dir)
            self.reload_registry(generated_dir)
        return self.get_generated_tool(mutation_id) or record

    def _approve_code_mutation(self, record: MutationRecord, approved_by: str) -> None:
        settings = get_mutation_settings()
        branch_name = record.metadata.get("branch_name")
        if not branch_name:
            raise ValueError("Code mutation has no branch_name in metadata")
        from keprix.mutation.self_coding_git import merge_mutation_branch

        repo_root = Path(settings.repo_root).resolve()
        merged = merge_mutation_branch(
            repo_root,
            str(branch_name),
            strategy=settings.merge_strategy,
            message=f"Approve code mutation {record.id}",
        )
        if not merged.ok:
            raise ValueError(merged.stderr or "merge failed; resolve conflicts manually")

        metadata = dict(record.metadata)
        metadata["merged"] = True
        metadata["merge_commit_hash"] = merged.commit_hash
        metadata["approved_by"] = approved_by
        self.update_status(record.id, "approved", approved_by=approved_by)
        self._set_status_and_metadata(record.id, "approved", metadata)

        files_changed = list(metadata.get("files_changed") or [])
        if any(str(path).startswith("src/keprix/tools/") for path in files_changed):
            self.reload_registry(self.generated_tools_dir())

    def reject_mutation(
        self,
        mutation_id: str,
        rejected_by: str,
        reason: str,
    ) -> MutationRecord | None:
        record = self.get_generated_tool(mutation_id)
        if record is None:
            return None
        if record.tier == "code":
            self._cleanup_code_branch(record)
        metadata = dict(record.metadata)
        metadata["rejected_by"] = rejected_by
        metadata["reject_reason"] = reason
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                conn.execute(
                    "UPDATE mutation_events SET status = ?, metadata = ? WHERE id = ?",
                    ("rejected", json.dumps(metadata), mutation_id),
                )
                conn.commit()
            row = self._fetch_sqlite(mutation_id)
            return _row_to_record(row) if row else None
        import asyncio

        return asyncio.run(self._reject_postgres(mutation_id, rejected_by, reason, metadata))

    def rollback_mutation(self, mutation_id: str, rolled_back_by: str) -> MutationRecord | None:
        record = self.get_generated_tool(mutation_id)
        if record is None:
            return None
        if record.tier == "code":
            self._rollback_code_mutation(record)
        if record.tier == "tool":
            generated_dir = self.generated_tools_dir()
            for suffix in (".py", ".sig", ".meta.json"):
                path = generated_dir / f"{record.name}{suffix}"
                if path.exists():
                    try:
                        path.unlink()
                    except OSError as exc:
                        logger.warning("could not delete %s during rollback: %s", path, exc)
            try:
                from tools.registry import registry

                registry.deregister_tool(record.name)
            except Exception as exc:
                logger.warning("could not deregister tool %s: %s", record.name, exc)

        metadata = dict(record.metadata)
        metadata["rolled_back_by"] = rolled_back_by
        self._set_status_and_metadata(mutation_id, "rolled_back", metadata)

        now = datetime.now(timezone.utc)
        rollback_id = str(uuid.uuid4())
        rollback_row = {
            "id": rollback_id,
            "recorded_at": now,
            "workspace_id": record.workspace_id,
            "tier": record.tier,
            "trigger": "rollback",
            "status": "rolled_back",
            "name": record.name,
            "description": record.description,
            "source_code": record.source_code,
            "before_value": None,
            "after_value": None,
            "approved_by": rolled_back_by,
            "approved_at": now,
            "quality_score": record.quality_score,
            "use_count": 0,
            "last_used_at": None,
            "rollback_of": mutation_id,
            "metadata": {"rolled_back_by": rolled_back_by},
        }
        if self._use_sqlite():
            self._insert_sqlite(rollback_row)
        else:
            self._insert_postgres_sync(rollback_row)
        return _row_to_record(rollback_row)

    def _cleanup_code_branch(self, record: MutationRecord) -> None:
        branch_name = record.metadata.get("branch_name")
        if not branch_name:
            return
        try:
            from keprix.mutation.self_coding_git import delete_branch

            repo_root = Path(get_mutation_settings().repo_root).resolve()
            delete_branch(repo_root, str(branch_name))
        except Exception as exc:
            logger.warning("could not delete mutation branch %s: %s", branch_name, exc)

    def _rollback_code_mutation(self, record: MutationRecord) -> None:
        branch_name = record.metadata.get("branch_name")
        if not branch_name:
            return
        try:
            from keprix.mutation.self_coding_git import revert_or_delete_mutation_branch

            repo_root = Path(get_mutation_settings().repo_root).resolve()
            revert_or_delete_mutation_branch(
                repo_root,
                str(branch_name),
                merged=bool(record.metadata.get("merged")),
                merge_commit_hash=record.metadata.get("merge_commit_hash"),
            )
        except Exception as exc:
            logger.warning("could not rollback code mutation branch %s: %s", branch_name, exc)

    def _set_status_and_metadata(self, record_id: str, status: str, metadata: dict[str, Any]) -> None:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                conn.execute(
                    "UPDATE mutation_events SET status = ?, metadata = ? WHERE id = ?",
                    (status, json.dumps(metadata), record_id),
                )
                conn.commit()
            return
        import asyncio

        asyncio.run(self._set_status_metadata_postgres(record_id, status, metadata))

    def _list_mutations_sqlite(
        self,
        workspace_id: str,
        *,
        tier: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM mutation_events WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if tier:
            query += " AND tier = ?"
            params.append(tier)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY recorded_at DESC"
        with self._sqlite_conn() as conn:
            cur = conn.execute(query, params)
            columns = [part[0] for part in cur.description]
            return [_sqlite_row_dict(columns, row) for row in cur.fetchall()]

    async def _list_mutations_postgres(
        self,
        workspace_id: str,
        *,
        tier: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            return self._list_mutations_sqlite(workspace_id, tier=tier, status=status)
        query = select(MutationEventRow).where(MutationEventRow.workspace_id == workspace_id)
        if tier:
            query = query.where(MutationEventRow.tier == tier)
        if status:
            query = query.where(MutationEventRow.status == status)
        query = query.order_by(MutationEventRow.recorded_at.desc())
        async with factory() as session:
            result = await session.execute(query)
            entries = result.scalars().all()
        rows: list[dict[str, Any]] = []
        for entry in entries:
            rows.append(
                {
                    "id": entry.id,
                    "recorded_at": entry.recorded_at,
                    "workspace_id": entry.workspace_id,
                    "tier": entry.tier,
                    "trigger": entry.trigger,
                    "status": entry.status,
                    "name": entry.name,
                    "description": entry.description,
                    "source_code": entry.source_code,
                    "before_value": entry.before_value,
                    "after_value": entry.after_value,
                    "approved_by": entry.approved_by,
                    "approved_at": entry.approved_at,
                    "quality_score": entry.quality_score,
                    "use_count": entry.use_count,
                    "last_used_at": entry.last_used_at,
                    "rollback_of": entry.rollback_of,
                    "metadata": dict(entry.metadata_json or {}),
                }
            )
        return rows

    async def _reject_postgres(
        self,
        mutation_id: str,
        rejected_by: str,
        reason: str,
        metadata: dict[str, Any],
    ) -> MutationRecord | None:
        factory = get_session_factory()
        if factory is None:
            with self._sqlite_conn() as conn:
                conn.execute(
                    "UPDATE mutation_events SET status = ?, metadata = ? WHERE id = ?",
                    ("rejected", json.dumps(metadata), mutation_id),
                )
                conn.commit()
            row = self._fetch_sqlite(mutation_id)
            return _row_to_record(row) if row else None
        async with factory() as session:
            result = await session.execute(select(MutationEventRow).where(MutationEventRow.id == mutation_id))
            entry = result.scalar_one_or_none()
            if entry is None:
                return None
            entry.status = "rejected"
            entry.metadata_json = metadata
            await session.commit()
            return _entry_to_record(entry)

    async def _set_status_metadata_postgres(
        self,
        record_id: str,
        status: str,
        metadata: dict[str, Any],
    ) -> None:
        factory = get_session_factory()
        if factory is None:
            self._set_status_and_metadata(record_id, status, metadata)
            return
        async with factory() as session:
            result = await session.execute(select(MutationEventRow).where(MutationEventRow.id == record_id))
            entry = result.scalar_one_or_none()
            if entry is None:
                return
            entry.status = status
            entry.metadata_json = metadata
            await session.commit()

    def _insert_sqlite(self, row: dict[str, Any]) -> None:
        with self._sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO mutation_events (
                    id, recorded_at, workspace_id, tier, trigger, status, name, description,
                    source_code, before_value, after_value, approved_by, approved_at,
                    quality_score, use_count, last_used_at, rollback_of, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["recorded_at"].isoformat(),
                    row["workspace_id"],
                    row["tier"],
                    row["trigger"],
                    row["status"],
                    row["name"],
                    row["description"],
                    row["source_code"],
                    row["before_value"],
                    row["after_value"],
                    row["approved_by"],
                    row["approved_at"].isoformat() if row["approved_at"] else None,
                    row["quality_score"],
                    row["use_count"],
                    None,
                    row["rollback_of"],
                    json.dumps(row["metadata"]),
                ),
            )
            conn.commit()

    def _fetch_sqlite(self, record_id: str) -> dict[str, Any] | None:
        with self._sqlite_conn() as conn:
            cur = conn.execute("SELECT * FROM mutation_events WHERE id = ?", (record_id,))
            row = cur.fetchone()
            if row is None:
                return None
            columns = [part[0] for part in cur.description]
            return _sqlite_row_dict(columns, row)

    def _list_sqlite(self, workspace_id: str, *, status: str | None) -> list[dict[str, Any]]:
        query = "SELECT * FROM mutation_events WHERE workspace_id = ? AND tier = 'tool'"
        params: list[Any] = [workspace_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        with self._sqlite_conn() as conn:
            cur = conn.execute(query, params)
            columns = [part[0] for part in cur.description]
            return [_sqlite_row_dict(columns, row) for row in cur.fetchall()]

    async def _insert_postgres(self, row: dict[str, Any]) -> None:
        factory = get_session_factory()
        if factory is None:
            self._insert_sqlite(row)
            return
        entry = MutationEventRow(
            id=row["id"],
            recorded_at=row["recorded_at"],
            workspace_id=row["workspace_id"],
            tier=row["tier"],
            trigger=row["trigger"],
            status=row["status"],
            name=row["name"],
            description=row["description"],
            source_code=row["source_code"],
            before_value=row["before_value"],
            after_value=row["after_value"],
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            quality_score=row["quality_score"],
            use_count=row["use_count"],
            metadata_json=row["metadata"],
        )
        async with factory() as session:
            session.add(entry)
            await session.commit()

    async def _fetch_postgres(self, record_id: str) -> MutationRecord | None:
        factory = get_session_factory()
        if factory is None:
            row = self._fetch_sqlite(record_id)
            return _row_to_record(row) if row else None
        async with factory() as session:
            result = await session.execute(select(MutationEventRow).where(MutationEventRow.id == record_id))
            entry = result.scalar_one_or_none()
            if entry is None:
                return None
            return _entry_to_record(entry)

    async def _list_postgres(self, workspace_id: str, *, status: str | None) -> list[MutationRecord]:
        factory = get_session_factory()
        if factory is None:
            return [_row_to_record(row) for row in self._list_sqlite(workspace_id, status=status)]
        query = select(MutationEventRow).where(
            MutationEventRow.workspace_id == workspace_id,
            MutationEventRow.tier == "tool",
        )
        if status:
            query = query.where(MutationEventRow.status == status)
        async with factory() as session:
            result = await session.execute(query)
            return [_entry_to_record(entry) for entry in result.scalars().all()]

    async def _update_status_postgres(
        self,
        record_id: str,
        status: str,
        *,
        approved_by: str | None,
    ) -> MutationRecord | None:
        factory = get_session_factory()
        if factory is None:
            return self.update_status(record_id, status, approved_by=approved_by)
        async with factory() as session:
            result = await session.execute(select(MutationEventRow).where(MutationEventRow.id == record_id))
            entry = result.scalar_one_or_none()
            if entry is None:
                return None
            entry.status = status
            entry.approved_by = approved_by
            if status == "approved":
                entry.approved_at = datetime.now(timezone.utc)
            await session.commit()
            return _entry_to_record(entry)


_store: MutationStore | None = None


def get_mutation_store() -> MutationStore:
    global _store
    if _store is None:
        _store = MutationStore()
    return _store


def _sqlite_row_dict(columns: list[str], row: tuple[Any, ...]) -> dict[str, Any]:
    data = dict(zip(columns, row))
    data["recorded_at"] = datetime.fromisoformat(str(data["recorded_at"]))
    approved_at = data.get("approved_at")
    data["approved_at"] = datetime.fromisoformat(approved_at) if approved_at else None
    last_used_at = data.get("last_used_at")
    data["last_used_at"] = datetime.fromisoformat(last_used_at) if last_used_at else None
    metadata = data.get("metadata") or "{}"
    data["metadata"] = json.loads(metadata) if isinstance(metadata, str) else metadata
    return data


def _row_to_record(row: dict[str, Any]) -> MutationRecord:
    return MutationRecord(
        id=str(row["id"]),
        recorded_at=row["recorded_at"],
        workspace_id=str(row["workspace_id"]),
        tier=str(row["tier"]),
        trigger=str(row["trigger"]),
        status=str(row["status"]),
        name=str(row["name"]),
        description=row.get("description"),
        source_code=row.get("source_code"),
        before_value=row.get("before_value"),
        after_value=row.get("after_value"),
        approved_by=row.get("approved_by"),
        approved_at=row.get("approved_at"),
        quality_score=float(row["quality_score"]) if row.get("quality_score") is not None else None,
        use_count=int(row.get("use_count") or 0),
        last_used_at=_parse_optional_datetime(row.get("last_used_at")),
        metadata=dict(row.get("metadata") or {}),
    )


def _entry_to_record(entry: MutationEventRow) -> MutationRecord:
    return MutationRecord(
        id=entry.id,
        recorded_at=entry.recorded_at,
        workspace_id=entry.workspace_id,
        tier=entry.tier,
        trigger=entry.trigger,
        status=entry.status,
        name=entry.name,
        description=entry.description,
        source_code=entry.source_code,
        before_value=entry.before_value,
        after_value=entry.after_value,
        approved_by=entry.approved_by,
        approved_at=entry.approved_at,
        quality_score=entry.quality_score,
        use_count=entry.use_count,
        last_used_at=entry.last_used_at,
        metadata=dict(entry.metadata_json or {}),
    )


def _parse_optional_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _quality_sample_dict(columns: list[str], row: tuple[Any, ...]) -> dict[str, Any]:
    data = dict(zip(columns, row))
    sampled_at = data.get("sampled_at")
    data["sampled_at"] = datetime.fromisoformat(str(sampled_at)) if sampled_at else datetime.now(timezone.utc)
    return data
