"""PostgreSQL-backed metrics collection with 90-day retention."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Numeric, String, Text, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.database import Base, get_session_factory

RETENTION_DAYS = 90
logger = logging.getLogger(__name__)


class MetricEntry(Base):
    __tablename__ = "metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric_type: Mapped[str] = mapped_column(Text, nullable=False)
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    tags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def _is_missing_relation(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "undefinedtable" in text or ("does not exist" in text and "metrics" in text)


class MetricsStore:
    async def record(
        self,
        *,
        metric_type: str,
        metric_name: str,
        metric_value: float | int,
        user_id: str | None = None,
        tags: dict[str, Any] | None = None,
    ) -> None:
        factory = get_session_factory()
        if factory is None:
            return
        entry = MetricEntry(
            user_id=user_id,
            metric_type=metric_type,
            metric_name=metric_name,
            metric_value=Decimal(str(metric_value)),
            tags=tags or {},
        )
        try:
            async with factory() as session:
                session.add(entry)
                await session.commit()
        except Exception as exc:
            if _is_missing_relation(exc):
                logger.warning("metrics table missing; skipped record (%s)", exc)
                return
            raise

    async def prune_old(self) -> int:
        factory = get_session_factory()
        if factory is None:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        try:
            async with factory() as session:
                result = await session.execute(
                    delete(MetricEntry).where(MetricEntry.recorded_at < cutoff)
                )
                await session.commit()
                return int(result.rowcount or 0)
        except Exception as exc:
            if _is_missing_relation(exc):
                logger.warning("metrics table missing; skipped prune (%s)", exc)
                return 0
            raise

    async def sum_by_day(
        self,
        *,
        metric_type: str,
        days: int = 30,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            async with factory() as session:
                day_expr = func.date_trunc("day", MetricEntry.recorded_at).label("day")
                query = (
                    select(
                        day_expr,
                        func.sum(MetricEntry.metric_value).label("total"),
                    )
                    .where(MetricEntry.metric_type == metric_type)
                    .where(MetricEntry.recorded_at >= cutoff)
                    .group_by(day_expr)
                    .order_by(day_expr)
                )
                if user_id:
                    query = query.where(MetricEntry.user_id == user_id)
                rows = (await session.execute(query)).all()
                return [
                    {"date": row.day.date().isoformat(), "total": float(row.total or 0)}
                    for row in rows
                ]
        except Exception as exc:
            if _is_missing_relation(exc):
                logger.warning("metrics table missing; sum_by_day empty (%s)", exc)
                return []
            raise

    async def breakdown(
        self,
        *,
        metric_type: str,
        days: int = 30,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            async with factory() as session:
                query = (
                    select(
                        MetricEntry.metric_name.label("name"),
                        func.count().label("count"),
                        func.sum(MetricEntry.metric_value).label("total"),
                    )
                    .where(MetricEntry.metric_type == metric_type)
                    .where(MetricEntry.recorded_at >= cutoff)
                    .group_by(MetricEntry.metric_name)
                    .order_by(func.sum(MetricEntry.metric_value).desc())
                )
                if user_id:
                    query = query.where(MetricEntry.user_id == user_id)
                rows = (await session.execute(query)).all()
                return [
                    {"name": row.name, "count": int(row.count), "total": float(row.total or 0)}
                    for row in rows
                ]
        except Exception as exc:
            if _is_missing_relation(exc):
                logger.warning("metrics table missing; breakdown empty (%s)", exc)
                return []
            raise

    async def rate_limit_events(self, days: int = 30) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            async with factory() as session:
                rows = (
                    await session.execute(
                        select(MetricEntry)
                        .where(MetricEntry.metric_type == "provider_request")
                        .where(MetricEntry.recorded_at >= cutoff)
                    )
                ).scalars().all()
        except Exception as exc:
            if _is_missing_relation(exc):
                logger.warning("metrics table missing; rate_limit_events empty (%s)", exc)
                return []
            raise
        counts: dict[str, int] = {}
        for row in rows:
            if row.tags.get("rate_limited"):
                counts[row.metric_name] = counts.get(row.metric_name, 0) + 1
        return [{"provider": name, "events": count} for name, count in sorted(counts.items())]


_metrics_store: MetricsStore | None = None


def get_metrics_store() -> MetricsStore:
    global _metrics_store
    if _metrics_store is None:
        _metrics_store = MetricsStore()
    return _metrics_store


async def record_rate_limit_event(provider: str, user_id: str | None = None) -> None:
    await get_metrics_store().record(
        metric_type="provider_request",
        metric_name=provider,
        metric_value=1,
        user_id=user_id,
        tags={"rate_limited": True},
    )
