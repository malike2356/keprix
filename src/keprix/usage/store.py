"""Persistent store for LLM usage events (PostgreSQL + SQLite fallback)."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, Numeric, String, Text, case, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.auth.config import data_dir
from keprix.database import Base, get_session_factory
from keprix.usage.config import get_llm_usage_config
from keprix.usage.filters import UsageQueryFilters
from keprix.usage.schemas import LlmUsageRecord

logger = logging.getLogger(__name__)

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_usage_events (
    id TEXT PRIMARY KEY,
    recorded_at TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    user_id TEXT,
    session_id TEXT,
    run_id TEXT,
    channel TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL,
    cost_status TEXT NOT NULL,
    cost_source TEXT NOT NULL,
    duration_ms INTEGER,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_llm_usage_recorded_at ON llm_usage_events(recorded_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_workspace_recorded ON llm_usage_events(workspace_id, recorded_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_user_recorded ON llm_usage_events(user_id, recorded_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_model_recorded ON llm_usage_events(model, recorded_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_channel_recorded ON llm_usage_events(channel, recorded_at);
"""


class LlmUsageEventRow(Base):
    __tablename__ = "llm_usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False, default="default")
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    cost_status: Mapped[str] = mapped_column(Text, nullable=False)
    cost_source: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class LlmUsageStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._sqlite_path = sqlite_path or Path(data_dir()) / "llm_usage.db"
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
        if get_session_factory() is not None:
            return False
        return get_llm_usage_config().sqlite_fallback

    def insert_sync(self, record: LlmUsageRecord) -> str:
        row = record.to_row()
        if self._use_sqlite():
            self._insert_sqlite(row)
            return record.id
        factory = get_session_factory()
        if factory is None:
            return record.id
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.insert_async(record))
            return record.id
        loop.create_task(self.insert_async(record))
        return record.id

    async def insert_async(self, record: LlmUsageRecord) -> str:
        row = record.to_row()
        if self._use_sqlite():
            self._insert_sqlite(row)
            return record.id
        factory = get_session_factory()
        if factory is None:
            return record.id
        entry = LlmUsageEventRow(
            id=row["id"],
            recorded_at=row["recorded_at"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            run_id=row["run_id"],
            channel=row["channel"],
            provider=row["provider"],
            model=row["model"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cache_read_tokens=row["cache_read_tokens"],
            cache_write_tokens=row["cache_write_tokens"],
            reasoning_tokens=row["reasoning_tokens"],
            total_tokens=row["total_tokens"],
            cost_usd=Decimal(str(row["cost_usd"])) if row["cost_usd"] is not None else None,
            cost_status=row["cost_status"],
            cost_source=row["cost_source"],
            duration_ms=row["duration_ms"],
            metadata_json=row["metadata"],
        )
        async with factory() as session:
            session.add(entry)
            await session.commit()
        return record.id

    def _insert_sqlite(self, row: dict[str, Any]) -> None:
        recorded_at = row["recorded_at"]
        if isinstance(recorded_at, datetime):
            recorded_at = recorded_at.astimezone(timezone.utc).isoformat()
        with self._sqlite_conn() as conn:
            conn.execute(
                """
                INSERT INTO llm_usage_events (
                    id, recorded_at, workspace_id, user_id, session_id, run_id, channel,
                    provider, model, input_tokens, output_tokens, cache_read_tokens,
                    cache_write_tokens, reasoning_tokens, total_tokens, cost_usd,
                    cost_status, cost_source, duration_ms, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    recorded_at,
                    row["workspace_id"],
                    row["user_id"],
                    row["session_id"],
                    row["run_id"],
                    row["channel"],
                    row["provider"],
                    row["model"],
                    row["input_tokens"],
                    row["output_tokens"],
                    row["cache_read_tokens"],
                    row["cache_write_tokens"],
                    row["reasoning_tokens"],
                    row["total_tokens"],
                    row["cost_usd"],
                    row["cost_status"],
                    row["cost_source"],
                    row["duration_ms"],
                    json.dumps(row["metadata"]),
                ),
            )
            conn.commit()

    def count_sync(self) -> int:
        if self._use_sqlite():
            with self._sqlite_conn() as conn:
                row = conn.execute("SELECT COUNT(*) FROM llm_usage_events").fetchone()
                return int(row[0] if row else 0)
        return 0

    def list_since_sync(self, *, since: datetime) -> list[dict[str, Any]]:
        if self._use_sqlite():
            since_iso = since.astimezone(timezone.utc).isoformat()
            with self._sqlite_conn() as conn:
                rows = conn.execute(
                    "SELECT id, model, total_tokens, cost_usd FROM llm_usage_events WHERE recorded_at >= ?",
                    (since_iso,),
                ).fetchall()
            return [
                {"id": row[0], "model": row[1], "total_tokens": row[2], "cost_usd": row[3]}
                for row in rows
            ]
        return []

    def prune_sync(self, *, retention_days: int | None = None) -> int:
        days = retention_days or get_llm_usage_config().retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        if self._use_sqlite():
            cutoff_iso = cutoff.isoformat()
            with self._sqlite_conn() as conn:
                cur = conn.execute(
                    "DELETE FROM llm_usage_events WHERE recorded_at < ?",
                    (cutoff_iso,),
                )
                conn.commit()
                return int(cur.rowcount or 0)
        return 0

    async def prune_async(self, *, retention_days: int | None = None) -> int:
        days = retention_days or get_llm_usage_config().retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        if self._use_sqlite():
            return self.prune_sync(retention_days=days)
        factory = get_session_factory()
        if factory is None:
            return 0
        async with factory() as session:
            result = await session.execute(
                delete(LlmUsageEventRow).where(LlmUsageEventRow.recorded_at < cutoff)
            )
            await session.commit()
            return int(result.rowcount or 0)

    def _sqlite_where(self, filters: UsageQueryFilters) -> tuple[str, list[Any]]:
        since, until = filters.window()
        clauses = ["recorded_at >= ?", "recorded_at <= ?"]
        params: list[Any] = [since.isoformat(), until.isoformat()]
        if filters.workspace_id:
            clauses.append("workspace_id = ?")
            params.append(filters.workspace_id)
        if filters.user_id:
            clauses.append("user_id = ?")
            params.append(filters.user_id)
        if filters.channel:
            clauses.append("channel = ?")
            params.append(filters.channel)
        if filters.model:
            clauses.append("model = ?")
            params.append(filters.model)
        if filters.provider:
            clauses.append("provider = ?")
            params.append(filters.provider)
        return " AND ".join(clauses), params

    def _pg_apply_filters(self, query, filters: UsageQueryFilters):
        since, until = filters.window()
        query = query.where(LlmUsageEventRow.recorded_at >= since)
        query = query.where(LlmUsageEventRow.recorded_at <= until)
        if filters.workspace_id:
            query = query.where(LlmUsageEventRow.workspace_id == filters.workspace_id)
        if filters.user_id:
            query = query.where(LlmUsageEventRow.user_id == filters.user_id)
        if filters.channel:
            query = query.where(LlmUsageEventRow.channel == filters.channel)
        if filters.model:
            query = query.where(LlmUsageEventRow.model == filters.model)
        if filters.provider:
            query = query.where(LlmUsageEventRow.provider == filters.provider)
        return query

    def aggregate_summary_sync(self, filters: UsageQueryFilters) -> dict[str, Any]:
        if not self._use_sqlite():
            return {}
        where_sql, params = self._sqlite_where(filters)
        with self._sqlite_conn() as conn:
            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS request_count,
                    COALESCE(SUM(input_tokens), 0),
                    COALESCE(SUM(output_tokens), 0),
                    COALESCE(SUM(cache_read_tokens), 0),
                    COALESCE(SUM(total_tokens), 0),
                    COALESCE(SUM(cost_usd), 0),
                    SUM(CASE WHEN cost_status = 'estimated' THEN cost_usd ELSE 0 END),
                    SUM(CASE WHEN cost_status = 'unknown' OR cost_usd IS NULL THEN 1 ELSE 0 END)
                FROM llm_usage_events
                WHERE {where_sql}
                """,
                params,
            ).fetchone()
        request_count = int(row[0] or 0)
        total_cost = float(row[5] or 0)
        return self._format_summary(filters, request_count, row, total_cost)

    def _format_summary(
        self,
        filters: UsageQueryFilters,
        request_count: int,
        row: Any,
        total_cost: float,
    ) -> dict[str, Any]:
        since, until = filters.window()
        period_days = max(1, int((until - since).total_seconds() // 86400) or filters.days or 30)
        input_tokens = int(row[1] or 0)
        output_tokens = int(row[2] or 0)
        cache_read = int(row[3] or 0)
        total_tokens = int(row[4] or 0)
        estimated_cost = float(row[6] or 0)
        unknown_cost_count = int(row[7] or 0)
        return {
            "period_days": period_days,
            "request_count": request_count,
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read,
            "total_cost_usd": round(total_cost, 6),
            "estimated_cost_usd": round(estimated_cost, 6),
            "unknown_cost_count": unknown_cost_count,
            "avg_cost_per_request_usd": round(total_cost / request_count, 6) if request_count else 0.0,
            "avg_tokens_per_request": round(total_tokens / request_count, 2) if request_count else 0.0,
        }

    async def aggregate_summary(self, filters: UsageQueryFilters) -> dict[str, Any]:
        if self._use_sqlite():
            return self.aggregate_summary_sync(filters)
        factory = get_session_factory()
        if factory is None:
            return self._empty_summary(filters)
        async with factory() as session:
            query = select(
                func.count().label("request_count"),
                func.coalesce(func.sum(LlmUsageEventRow.input_tokens), 0),
                func.coalesce(func.sum(LlmUsageEventRow.output_tokens), 0),
                func.coalesce(func.sum(LlmUsageEventRow.cache_read_tokens), 0),
                func.coalesce(func.sum(LlmUsageEventRow.total_tokens), 0),
                func.coalesce(func.sum(LlmUsageEventRow.cost_usd), 0),
                func.coalesce(
                    func.sum(
                        case(
                            (LlmUsageEventRow.cost_status == "estimated", LlmUsageEventRow.cost_usd),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (LlmUsageEventRow.cost_status == "unknown")
                                | (LlmUsageEventRow.cost_usd.is_(None)),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            query = self._pg_apply_filters(query, filters)
            row = (await session.execute(query)).one()
        request_count = int(row.request_count or 0)
        total_cost = float(row[5] or 0)
        return self._format_summary(filters, request_count, row, total_cost)

    def _empty_summary(self, filters: UsageQueryFilters) -> dict[str, Any]:
        return self._format_summary(filters, 0, (0, 0, 0, 0, 0, 0, 0, 0), 0.0)

    def aggregate_timeseries_sync(
        self,
        filters: UsageQueryFilters,
        *,
        granularity: str = "day",
    ) -> list[dict[str, Any]]:
        if not self._use_sqlite():
            return []
        fmt = "%Y-%m-%d" if granularity == "day" else "%Y-%m-%dT%H"
        where_sql, params = self._sqlite_where(filters)
        with self._sqlite_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    strftime('{fmt}', recorded_at) AS bucket,
                    COUNT(*) AS request_count,
                    COALESCE(SUM(total_tokens), 0),
                    COALESCE(SUM(cost_usd), 0)
                FROM llm_usage_events
                WHERE {where_sql}
                GROUP BY bucket
                ORDER BY bucket
                """,
                params,
            ).fetchall()
        return [
            {
                "date": row[0],
                "request_count": int(row[1] or 0),
                "total_tokens": int(row[2] or 0),
                "total_cost_usd": round(float(row[3] or 0), 6),
            }
            for row in rows
        ]

    async def aggregate_timeseries(
        self,
        filters: UsageQueryFilters,
        *,
        granularity: str = "day",
    ) -> list[dict[str, Any]]:
        if self._use_sqlite():
            return self.aggregate_timeseries_sync(filters, granularity=granularity)
        factory = get_session_factory()
        if factory is None:
            return []
        unit = "day" if granularity == "day" else "hour"
        bucket = func.date_trunc(unit, LlmUsageEventRow.recorded_at).label("bucket")
        query = (
            select(
                bucket,
                func.count().label("request_count"),
                func.coalesce(func.sum(LlmUsageEventRow.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(LlmUsageEventRow.cost_usd), 0).label("total_cost_usd"),
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        query = self._pg_apply_filters(query, filters)
        async with factory() as session:
            rows = (await session.execute(query)).all()
        return [
            {
                "date": row.bucket.date().isoformat()
                if granularity == "day" and hasattr(row.bucket, "date")
                else row.bucket.isoformat() if hasattr(row.bucket, "isoformat") else str(row.bucket),
                "request_count": int(row.request_count or 0),
                "total_tokens": int(row.total_tokens or 0),
                "total_cost_usd": round(float(row.total_cost_usd or 0), 6),
            }
            for row in rows
        ]

    def aggregate_breakdown_sync(
        self,
        filters: UsageQueryFilters,
        *,
        dimension: str,
    ) -> list[dict[str, Any]]:
        if not self._use_sqlite():
            return []
        column = self._dimension_column(dimension)
        where_sql, params = self._sqlite_where(filters)
        with self._sqlite_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    {column} AS dim_key,
                    COUNT(*) AS request_count,
                    COALESCE(SUM(total_tokens), 0),
                    COALESCE(SUM(cost_usd), 0)
                FROM llm_usage_events
                WHERE {where_sql}
                GROUP BY dim_key
                ORDER BY COALESCE(SUM(cost_usd), 0) DESC
                """,
                params,
            ).fetchall()
        return self._format_breakdown(rows)

    async def aggregate_breakdown(
        self,
        filters: UsageQueryFilters,
        *,
        dimension: str,
    ) -> list[dict[str, Any]]:
        if dimension in {"agent", "agents"}:
            return await self.aggregate_agent_breakdown(filters)
        if self._use_sqlite():
            return self.aggregate_breakdown_sync(filters, dimension=dimension)
        factory = get_session_factory()
        if factory is None:
            return []
        column = self._pg_dimension_column(dimension)
        query = (
            select(
                column.label("dim_key"),
                func.count().label("request_count"),
                func.coalesce(func.sum(LlmUsageEventRow.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(LlmUsageEventRow.cost_usd), 0).label("total_cost_usd"),
            )
            .group_by(column)
            .order_by(func.coalesce(func.sum(LlmUsageEventRow.cost_usd), 0).desc())
        )
        query = self._pg_apply_filters(query, filters)
        async with factory() as session:
            rows = (await session.execute(query)).all()
        return self._format_breakdown(
            [(row.dim_key, row.request_count, row.total_tokens, row.total_cost_usd) for row in rows]
        )

    def aggregate_agent_breakdown_sync(self, filters: UsageQueryFilters) -> list[dict[str, Any]]:
        if not self._use_sqlite():
            return []
        where_sql, params = self._sqlite_where(filters)
        with self._sqlite_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    COALESCE(
                        NULLIF(json_extract(metadata, '$.agent_id'), ''),
                        NULLIF(json_extract(metadata, '$.agent'), ''),
                        NULLIF(json_extract(metadata, '$.app_name'), ''),
                        NULLIF(channel, ''),
                        'unknown'
                    ) AS dim_key,
                    COUNT(*) AS request_count,
                    COALESCE(SUM(total_tokens), 0),
                    COALESCE(SUM(cost_usd), 0)
                FROM llm_usage_events
                WHERE {where_sql}
                GROUP BY dim_key
                ORDER BY COALESCE(SUM(cost_usd), 0) DESC
                """,
                params,
            ).fetchall()
        return self._format_breakdown(rows)

    async def aggregate_agent_breakdown(self, filters: UsageQueryFilters) -> list[dict[str, Any]]:
        if self._use_sqlite():
            return self.aggregate_agent_breakdown_sync(filters)
        factory = get_session_factory()
        if factory is None:
            return []
        query = select(LlmUsageEventRow)
        query = self._pg_apply_filters(query, filters)
        buckets: dict[str, dict[str, float]] = {}
        async with factory() as session:
            rows = (await session.execute(query.limit(10000))).scalars().all()
        for row in rows:
            meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            key = (
                str(meta.get("agent_id") or "").strip()
                or str(meta.get("agent") or "").strip()
                or str(meta.get("app_name") or "").strip()
                or str(row.channel or "").strip()
                or "unknown"
            )
            bucket = buckets.setdefault(key, {"request_count": 0, "total_tokens": 0, "total_cost_usd": 0.0})
            bucket["request_count"] += 1
            bucket["total_tokens"] += float(row.total_tokens or 0)
            bucket["total_cost_usd"] += float(row.cost_usd or 0)
        formatted = [
            (key, data["request_count"], data["total_tokens"], data["total_cost_usd"])
            for key, data in buckets.items()
        ]
        formatted.sort(key=lambda item: float(item[3] or 0), reverse=True)
        return self._format_breakdown(formatted)

    def _dimension_column(self, dimension: str) -> str:
        mapping = {
            "model": "model",
            "models": "model",
            "provider": "provider",
            "providers": "provider",
            "channel": "channel",
            "channels": "channel",
            "user": "user_id",
            "users": "user_id",
        }
        return mapping.get(dimension, "model")

    def _pg_dimension_column(self, dimension: str):
        name = self._dimension_column(dimension)
        return getattr(LlmUsageEventRow, name)

    def _format_breakdown(self, rows: list[Any]) -> list[dict[str, Any]]:
        total_cost = sum(float(row[3] or 0) for row in rows)
        out: list[dict[str, Any]] = []
        for row in rows:
            key = str(row[0] or "unknown")
            cost = float(row[3] or 0)
            out.append(
                {
                    "key": key,
                    "label": key,
                    "request_count": int(row[1] or 0),
                    "total_tokens": int(row[2] or 0),
                    "total_cost_usd": round(cost, 6),
                    "share_percent": round(cost / total_cost * 100, 2) if total_cost > 0 else 0.0,
                }
            )
        return out

    def list_events_sync(
        self,
        filters: UsageQueryFilters,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        if not self._use_sqlite():
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        where_sql, params = self._sqlite_where(filters)
        with self._sqlite_conn() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM llm_usage_events WHERE {where_sql}",
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT id, recorded_at, user_id, session_id, channel, provider, model,
                       total_tokens, cost_usd, cost_status
                FROM llm_usage_events
                WHERE {where_sql}
                ORDER BY recorded_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return {
            "items": [
                {
                    "id": row[0],
                    "recorded_at": row[1],
                    "user_id": row[2],
                    "session_id": row[3],
                    "channel": row[4],
                    "provider": row[5],
                    "model": row[6],
                    "total_tokens": row[7],
                    "cost_usd": row[8],
                    "cost_status": row[9],
                }
                for row in rows
            ],
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
        }

    async def list_events(
        self,
        filters: UsageQueryFilters,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        if self._use_sqlite():
            return self.list_events_sync(filters, limit=limit, offset=offset)
        factory = get_session_factory()
        if factory is None:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        count_query = select(func.count()).select_from(LlmUsageEventRow)
        count_query = self._pg_apply_filters(count_query, filters)
        query = select(LlmUsageEventRow)
        query = self._pg_apply_filters(query, filters)
        async with factory() as session:
            total = await session.scalar(count_query)
            rows = (
                await session.execute(
                    query.order_by(LlmUsageEventRow.recorded_at.desc()).limit(limit).offset(offset)
                )
            ).scalars().all()
        return {
            "items": [
                {
                    "id": row.id,
                    "recorded_at": row.recorded_at.isoformat(),
                    "user_id": row.user_id,
                    "session_id": row.session_id,
                    "channel": row.channel,
                    "provider": row.provider,
                    "model": row.model,
                    "total_tokens": row.total_tokens,
                    "cost_usd": float(row.cost_usd) if row.cost_usd is not None else None,
                    "cost_status": row.cost_status,
                }
                for row in rows
            ],
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
        }

    def iter_export_rows_sync(self, filters: UsageQueryFilters):
        if not self._use_sqlite():
            return
        where_sql, params = self._sqlite_where(filters)
        with self._sqlite_conn() as conn:
            cursor = conn.execute(
                f"""
                SELECT recorded_at, user_id, channel, provider, model, input_tokens, output_tokens,
                       total_tokens, cost_usd, cost_status, session_id, run_id
                FROM llm_usage_events
                WHERE {where_sql}
                ORDER BY recorded_at DESC
                """,
                params,
            )
            for row in cursor:
                yield row


_store: LlmUsageStore | None = None


def get_llm_usage_store() -> LlmUsageStore:
    global _store
    if _store is None:
        _store = LlmUsageStore()
    return _store
