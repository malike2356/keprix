"""Persistent storage for blind model comparisons (PostgreSQL + SQLite fallback)."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.auth.config import data_dir
from keprix.database import Base, get_session_factory

logger = logging.getLogger(__name__)

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS model_comparisons (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    model_a TEXT NOT NULL,
    model_b TEXT NOT NULL,
    response_a TEXT NOT NULL,
    response_b TEXT NOT NULL,
    winner TEXT CHECK (winner IN ('a','b','tie')),
    voted_at TEXT,
    created_at TEXT NOT NULL,
    latency_ms_a INTEGER,
    latency_ms_b INTEGER
);
CREATE INDEX IF NOT EXISTS ix_model_comparisons_user_created
    ON model_comparisons(user_id, created_at);
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ComparisonRecord:
    id: str
    user_id: str
    prompt: str
    model_a: str
    model_b: str
    response_a: str
    response_b: str
    winner: str | None = None
    voted_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)
    latency_ms_a: int | None = None
    latency_ms_b: int | None = None


class ModelComparisonRow(Base):
    __tablename__ = "model_comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_a: Mapped[str] = mapped_column(Text, nullable=False)
    model_b: Mapped[str] = mapped_column(Text, nullable=False)
    response_a: Mapped[str] = mapped_column(Text, nullable=False)
    response_b: Mapped[str] = mapped_column(Text, nullable=False)
    winner: Mapped[str | None] = mapped_column(Text, nullable=True)
    voted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latency_ms_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms_b: Mapped[int | None] = mapped_column(Integer, nullable=True)


def _row_to_record(row: dict[str, Any]) -> ComparisonRecord:
    voted_at = row.get("voted_at")
    created_at = row.get("created_at")
    if isinstance(voted_at, str):
        voted_at = datetime.fromisoformat(voted_at)
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    return ComparisonRecord(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        prompt=str(row["prompt"]),
        model_a=str(row["model_a"]),
        model_b=str(row["model_b"]),
        response_a=str(row["response_a"]),
        response_b=str(row["response_b"]),
        winner=row.get("winner"),
        voted_at=voted_at,
        created_at=created_at or _utcnow(),
        latency_ms_a=row.get("latency_ms_a"),
        latency_ms_b=row.get("latency_ms_b"),
    )


class CompareStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._sqlite_path = sqlite_path or Path(data_dir()) / "model_comparisons.db"
        self._sqlite_ready = False

    def _sqlite_conn(self) -> sqlite3.Connection:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._sqlite_path)
        conn.row_factory = sqlite3.Row
        if not self._sqlite_ready:
            conn.executescript(_SQLITE_SCHEMA)
            conn.commit()
            self._sqlite_ready = True
        return conn

    def _use_sqlite(self) -> bool:
        return get_session_factory() is None

    def create(
        self,
        *,
        user_id: str,
        prompt: str,
        model_a: str,
        model_b: str,
        response_a: str,
        response_b: str,
        latency_ms_a: int | None = None,
        latency_ms_b: int | None = None,
    ) -> ComparisonRecord:
        now = _utcnow()
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "prompt": prompt,
            "model_a": model_a,
            "model_b": model_b,
            "response_a": response_a,
            "response_b": response_b,
            "winner": None,
            "voted_at": None,
            "created_at": now,
            "latency_ms_a": latency_ms_a,
            "latency_ms_b": latency_ms_b,
        }
        if self._use_sqlite():
            self._insert_sqlite(row)
        else:
            self._insert_postgres_sync(row)
        return _row_to_record(row)

    def get(self, comparison_id: str, user_id: str | None = None) -> ComparisonRecord | None:
        if self._use_sqlite():
            row = self._fetch_sqlite(comparison_id)
        else:
            row = self._fetch_postgres_sync(comparison_id)
        if row is None:
            return None
        record = _row_to_record(row)
        if user_id is not None and record.user_id != user_id:
            return None
        return record

    def list_for_user(self, user_id: str, *, limit: int = 100) -> list[ComparisonRecord]:
        if self._use_sqlite():
            rows = self._list_sqlite(user_id, limit=limit)
        else:
            rows = self._list_postgres_sync(user_id, limit=limit)
        return [_row_to_record(row) for row in rows]

    def vote(self, comparison_id: str, user_id: str, winner: str) -> ComparisonRecord | None:
        record = self.get(comparison_id, user_id)
        if record is None or record.winner is not None:
            return None
        now = _utcnow()
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                conn.execute(
                    """
                    UPDATE model_comparisons
                    SET winner = ?, voted_at = ?
                    WHERE id = ? AND user_id = ? AND winner IS NULL
                    """,
                    (winner, now.isoformat(), comparison_id, user_id),
                )
                conn.commit()
            row = self._fetch_sqlite(comparison_id)
        else:
            row = self._vote_postgres_sync(comparison_id, user_id, winner, now)
        return _row_to_record(row) if row else None

    def leaderboard(self) -> list[dict[str, Any]]:
        records = self._all_voted()
        pairs: dict[tuple[str, str], dict[str, Any]] = {}
        for record in records:
            key = tuple(sorted([record.model_a, record.model_b]))
            stats = pairs.setdefault(
                key,
                {"model_a": key[0], "model_b": key[1], "a_wins": 0, "b_wins": 0, "ties": 0},
            )
            if record.winner == "tie":
                stats["ties"] += 1
            elif record.winner == "a":
                winner_model = record.model_a
            else:
                winner_model = record.model_b
            if record.winner != "tie":
                if winner_model == key[0]:
                    stats["a_wins"] += 1
                else:
                    stats["b_wins"] += 1
        out: list[dict[str, Any]] = []
        for stats in pairs.values():
            total = stats["a_wins"] + stats["b_wins"] + stats["ties"]
            if total == 0:
                continue
            out.append(
                {
                    "model_a": stats["model_a"],
                    "model_b": stats["model_b"],
                    "a_win_rate_pct": round(100 * stats["a_wins"] / total, 2),
                    "b_win_rate_pct": round(100 * stats["b_wins"] / total, 2),
                    "tie_rate_pct": round(100 * stats["ties"] / total, 2),
                    "comparisons": total,
                    "a_wins": stats["a_wins"],
                    "b_wins": stats["b_wins"],
                    "ties": stats["ties"],
                }
            )
        out.sort(key=lambda row: row["comparisons"], reverse=True)
        return out

    def model_leaderboard(self) -> list[dict[str, Any]]:
        records = self._all_voted()
        stats: dict[str, dict[str, int]] = {}
        for record in records:
            for model_id in (record.model_a, record.model_b):
                stats.setdefault(model_id, {"wins": 0, "losses": 0, "ties": 0})
            if record.winner == "tie":
                stats[record.model_a]["ties"] += 1
                stats[record.model_b]["ties"] += 1
            elif record.winner == "a":
                stats[record.model_a]["wins"] += 1
                stats[record.model_b]["losses"] += 1
            else:
                stats[record.model_b]["wins"] += 1
                stats[record.model_a]["losses"] += 1
        out: list[dict[str, Any]] = []
        for model_id, counts in stats.items():
            total = counts["wins"] + counts["losses"] + counts["ties"]
            if total == 0:
                continue
            out.append(
                {
                    "model_id": model_id,
                    "wins": counts["wins"],
                    "losses": counts["losses"],
                    "ties": counts["ties"],
                    "comparisons": total,
                    "win_rate_pct": round(100 * counts["wins"] / total, 2),
                }
            )
        out.sort(key=lambda row: (row["win_rate_pct"], row["comparisons"]), reverse=True)
        return out

    def _all_voted(self) -> list[ComparisonRecord]:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM model_comparisons WHERE winner IS NOT NULL ORDER BY created_at DESC"
                ).fetchall()
            return [_row_to_record(dict(row)) for row in rows]
        rows = self._list_voted_postgres_sync()
        return [_row_to_record(row) for row in rows]

    def _insert_sqlite(self, row: dict[str, Any]) -> None:
        with self._sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO model_comparisons (
                    id, user_id, prompt, model_a, model_b, response_a, response_b,
                    winner, voted_at, created_at, latency_ms_a, latency_ms_b
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["user_id"],
                    row["prompt"],
                    row["model_a"],
                    row["model_b"],
                    row["response_a"],
                    row["response_b"],
                    row.get("winner"),
                    row["voted_at"].isoformat() if row.get("voted_at") else None,
                    row["created_at"].isoformat()
                    if isinstance(row["created_at"], datetime)
                    else row["created_at"],
                    row.get("latency_ms_a"),
                    row.get("latency_ms_b"),
                ),
            )
            conn.commit()

    def _fetch_sqlite(self, comparison_id: str) -> dict[str, Any] | None:
        with self._sqlite_conn() as conn:
            row = conn.execute(
                "SELECT * FROM model_comparisons WHERE id = ?",
                (comparison_id,),
            ).fetchone()
        return dict(row) if row else None

    def _list_sqlite(self, user_id: str, *, limit: int) -> list[dict[str, Any]]:
        with self._sqlite_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM model_comparisons
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def _insert_postgres_sync(self, row: dict[str, Any]) -> None:
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._insert_postgres(row))
            return
        self._insert_sqlite(row)

    async def _insert_postgres(self, row: dict[str, Any]) -> None:
        factory = get_session_factory()
        if factory is None:
            self._insert_sqlite(row)
            return
        entry = ModelComparisonRow(
            id=row["id"],
            user_id=row["user_id"],
            prompt=row["prompt"],
            model_a=row["model_a"],
            model_b=row["model_b"],
            response_a=row["response_a"],
            response_b=row["response_b"],
            winner=row.get("winner"),
            voted_at=row.get("voted_at"),
            created_at=row["created_at"],
            latency_ms_a=row.get("latency_ms_a"),
            latency_ms_b=row.get("latency_ms_b"),
        )
        async with factory() as session:
            session.add(entry)
            await session.commit()

    def _fetch_postgres_sync(self, comparison_id: str) -> dict[str, Any] | None:
        import asyncio

        return asyncio.run(self._fetch_postgres(comparison_id))

    async def _fetch_postgres(self, comparison_id: str) -> dict[str, Any] | None:
        factory = get_session_factory()
        if factory is None:
            return self._fetch_sqlite(comparison_id)
        async with factory() as session:
            row = await session.get(ModelComparisonRow, comparison_id)
            if row is None:
                return None
            return {
                "id": row.id,
                "user_id": row.user_id,
                "prompt": row.prompt,
                "model_a": row.model_a,
                "model_b": row.model_b,
                "response_a": row.response_a,
                "response_b": row.response_b,
                "winner": row.winner,
                "voted_at": row.voted_at,
                "created_at": row.created_at,
                "latency_ms_a": row.latency_ms_a,
                "latency_ms_b": row.latency_ms_b,
            }

    def _list_postgres_sync(self, user_id: str, *, limit: int) -> list[dict[str, Any]]:
        import asyncio

        return asyncio.run(self._list_postgres(user_id, limit=limit))

    async def _list_postgres(self, user_id: str, *, limit: int) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            return self._list_sqlite(user_id, limit=limit)
        async with factory() as session:
            result = await session.execute(
                select(ModelComparisonRow)
                .where(ModelComparisonRow.user_id == user_id)
                .order_by(ModelComparisonRow.created_at.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "prompt": row.prompt,
                "model_a": row.model_a,
                "model_b": row.model_b,
                "response_a": row.response_a,
                "response_b": row.response_b,
                "winner": row.winner,
                "voted_at": row.voted_at,
                "created_at": row.created_at,
                "latency_ms_a": row.latency_ms_a,
                "latency_ms_b": row.latency_ms_b,
            }
            for row in rows
        ]

    def _vote_postgres_sync(
        self,
        comparison_id: str,
        user_id: str,
        winner: str,
        voted_at: datetime,
    ) -> dict[str, Any] | None:
        import asyncio

        return asyncio.run(self._vote_postgres(comparison_id, user_id, winner, voted_at))

    async def _vote_postgres(
        self,
        comparison_id: str,
        user_id: str,
        winner: str,
        voted_at: datetime,
    ) -> dict[str, Any] | None:
        factory = get_session_factory()
        if factory is None:
            with self._sqlite_conn() as conn:
                conn.execute(
                    """
                    UPDATE model_comparisons
                    SET winner = ?, voted_at = ?
                    WHERE id = ? AND user_id = ? AND winner IS NULL
                    """,
                    (winner, voted_at.isoformat(), comparison_id, user_id),
                )
                conn.commit()
            return self._fetch_sqlite(comparison_id)
        async with factory() as session:
            row = await session.get(ModelComparisonRow, comparison_id)
            if row is None or row.user_id != user_id or row.winner is not None:
                return None
            row.winner = winner
            row.voted_at = voted_at
            await session.commit()
            await session.refresh(row)
            return {
                "id": row.id,
                "user_id": row.user_id,
                "prompt": row.prompt,
                "model_a": row.model_a,
                "model_b": row.model_b,
                "response_a": row.response_a,
                "response_b": row.response_b,
                "winner": row.winner,
                "voted_at": row.voted_at,
                "created_at": row.created_at,
                "latency_ms_a": row.latency_ms_a,
                "latency_ms_b": row.latency_ms_b,
            }

    def _list_voted_postgres_sync(self) -> list[dict[str, Any]]:
        import asyncio

        return asyncio.run(self._list_voted_postgres())

    async def _list_voted_postgres(self) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            with self._sqlite_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM model_comparisons WHERE winner IS NOT NULL ORDER BY created_at DESC"
                ).fetchall()
            return [dict(row) for row in rows]
        async with factory() as session:
            result = await session.execute(
                select(ModelComparisonRow)
                .where(ModelComparisonRow.winner.is_not(None))
                .order_by(ModelComparisonRow.created_at.desc())
            )
            rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "prompt": row.prompt,
                "model_a": row.model_a,
                "model_b": row.model_b,
                "response_a": row.response_a,
                "response_b": row.response_b,
                "winner": row.winner,
                "voted_at": row.voted_at,
                "created_at": row.created_at,
                "latency_ms_a": row.latency_ms_a,
                "latency_ms_b": row.latency_ms_b,
            }
            for row in rows
        ]


_store: CompareStore | None = None


def get_compare_store() -> CompareStore:
    global _store
    if _store is None:
        _store = CompareStore()
    return _store


def reset_compare_store(store: CompareStore | None = None) -> None:
    """Test helper to inject an isolated store instance."""
    global _store
    _store = store
