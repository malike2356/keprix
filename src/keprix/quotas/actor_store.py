"""Persistent actor quota counters (day buckets; month = sum of days)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.quotas.scope import QuotaScope

_SCHEMA = """
CREATE TABLE IF NOT EXISTS actor_quota_counters (
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    day TEXT NOT NULL,
    service TEXT NOT NULL DEFAULT '',
    calls INTEGER NOT NULL DEFAULT 0,
    tokens INTEGER NOT NULL DEFAULT 0,
    tool_runs INTEGER NOT NULL DEFAULT 0,
    mutation_runs INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scope_type, scope_id, day, service)
);
CREATE INDEX IF NOT EXISTS ix_actor_quota_scope_day
    ON actor_quota_counters(scope_type, scope_id, day);
CREATE TABLE IF NOT EXISTS actor_quota_overrides (
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    limits_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (scope_type, scope_id)
);
CREATE TABLE IF NOT EXISTS actor_quota_denials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    service TEXT,
    metric TEXT,
    reason TEXT,
    detail_json TEXT NOT NULL DEFAULT '{}',
    workspace_id TEXT,
    run_id TEXT
);
"""


def utc_day(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")


def period_start_day(period: str, now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    if period == "day":
        return utc_day(dt)
    return f"{dt.year:04d}-{dt.month:02d}-01"


@dataclass
class ActorUsage:
    calls: int = 0
    tokens: int = 0
    tool_runs: int = 0
    mutation_runs: int = 0
    per_service: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "tokens": self.tokens,
            "tool_runs": self.tool_runs,
            "mutation_runs": self.mutation_runs,
            "per_service": {k: dict(v) for k, v in self.per_service.items()},
        }


class ActorQuotaStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._path = sqlite_path or Path(data_dir()) / "actor_quotas.db"
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

    def get_usage(self, scope: QuotaScope, *, period: str = "month") -> ActorUsage:
        start = period_start_day(period)
        usage = ActorUsage()
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT service,
                       SUM(calls) AS calls,
                       SUM(tokens) AS tokens,
                       SUM(tool_runs) AS tool_runs,
                       SUM(mutation_runs) AS mutation_runs
                FROM actor_quota_counters
                WHERE scope_type = ? AND scope_id = ? AND day >= ?
                GROUP BY service
                """,
                (scope.scope_type, scope.scope_id, start),
            ).fetchall()
        for row in rows:
            service = (row["service"] or "").lower()
            calls = int(row["calls"] or 0)
            tokens = int(row["tokens"] or 0)
            tool_runs = int(row["tool_runs"] or 0)
            mutation_runs = int(row["mutation_runs"] or 0)
            usage.calls += calls
            usage.tokens += tokens
            usage.tool_runs += tool_runs
            usage.mutation_runs += mutation_runs
            if service:
                usage.per_service[service] = {
                    "calls": calls,
                    "tokens": tokens,
                    "tool_runs": tool_runs,
                    "mutation_runs": mutation_runs,
                }
        return usage

    def record(
        self,
        scope: QuotaScope,
        *,
        service: str = "",
        calls: int = 0,
        tokens: int = 0,
        tool_runs: int = 0,
        mutation_runs: int = 0,
        day: str | None = None,
    ) -> None:
        day_key = day or utc_day()
        svc = (service or "").lower()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO actor_quota_counters (
                    scope_type, scope_id, day, service, calls, tokens, tool_runs, mutation_runs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scope_type, scope_id, day, service) DO UPDATE SET
                    calls = calls + excluded.calls,
                    tokens = tokens + excluded.tokens,
                    tool_runs = tool_runs + excluded.tool_runs,
                    mutation_runs = mutation_runs + excluded.mutation_runs
                """,
                (
                    scope.scope_type,
                    scope.scope_id,
                    day_key,
                    svc,
                    max(0, int(calls)),
                    max(0, int(tokens)),
                    max(0, int(tool_runs)),
                    max(0, int(mutation_runs)),
                ),
            )
            conn.commit()

    def get_override(self, scope: QuotaScope) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT limits_json FROM actor_quota_overrides WHERE scope_type = ? AND scope_id = ?",
                (scope.scope_type, scope.scope_id),
            ).fetchone()
        if not row:
            return None
        try:
            data = json.loads(row["limits_json"] or "{}")
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def set_override(self, scope: QuotaScope, limits: dict[str, Any] | None) -> dict[str, Any] | None:
        with self._conn() as conn:
            if not limits:
                conn.execute(
                    "DELETE FROM actor_quota_overrides WHERE scope_type = ? AND scope_id = ?",
                    (scope.scope_type, scope.scope_id),
                )
                conn.commit()
                return None
            conn.execute(
                """
                INSERT INTO actor_quota_overrides (scope_type, scope_id, limits_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scope_type, scope_id) DO UPDATE SET
                    limits_json = excluded.limits_json,
                    updated_at = excluded.updated_at
                """,
                (
                    scope.scope_type,
                    scope.scope_id,
                    json.dumps(limits),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        return limits

    def record_denial(
        self,
        scope: QuotaScope,
        *,
        reason: str,
        metric: str | None = None,
        service: str | None = None,
        detail: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO actor_quota_denials (
                    created_at, scope_type, scope_id, service, metric, reason,
                    detail_json, workspace_id, run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    scope.scope_type,
                    scope.scope_id,
                    service,
                    metric,
                    reason,
                    json.dumps(detail or {}),
                    workspace_id,
                    run_id,
                ),
            )
            conn.commit()

    def list_denials(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM actor_quota_denials
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, min(int(limit), 500)),),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                detail = json.loads(row["detail_json"] or "{}")
            except Exception:
                detail = {}
            out.append(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "scope_type": row["scope_type"],
                    "scope_id": row["scope_id"],
                    "service": row["service"],
                    "metric": row["metric"],
                    "reason": row["reason"],
                    "detail": detail,
                    "workspace_id": row["workspace_id"],
                    "run_id": row["run_id"],
                }
            )
        return out


_store: ActorQuotaStore | None = None


def get_actor_quota_store() -> ActorQuotaStore:
    global _store
    if _store is None:
        _store = ActorQuotaStore()
    return _store


def reset_actor_quota_store_for_tests(store: ActorQuotaStore | None = None) -> ActorQuotaStore:
    global _store
    _store = store if store is not None else ActorQuotaStore()
    return _store
