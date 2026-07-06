"""HTTP request logging for the API server."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.database import Base, get_session_factory


class RequestLogEntry(Base):
    __tablename__ = "request_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    method: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class RequestLogStore:
    async def log(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str | None = None,
    ) -> None:
        factory = get_session_factory()
        if factory is None:
            return
        entry = RequestLogEntry(
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=Decimal(str(round(duration_ms, 2))),
            user_id=user_id,
        )
        async with factory() as session:
            session.add(entry)
            await session.commit()

    async def recent(self, limit: int = 100) -> list[dict]:
        factory = get_session_factory()
        if factory is None:
            return []
        async with factory() as session:
            rows = (
                await session.execute(
                    select(RequestLogEntry)
                    .order_by(RequestLogEntry.recorded_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
            return [
                {
                    "method": row.method,
                    "path": row.path,
                    "status_code": row.status_code,
                    "duration_ms": float(row.duration_ms),
                    "recorded_at": row.recorded_at.isoformat(),
                }
                for row in rows
            ]


_request_log_store: RequestLogStore | None = None


def get_request_log_store() -> RequestLogStore:
    global _request_log_store
    if _request_log_store is None:
        _request_log_store = RequestLogStore()
    return _request_log_store
