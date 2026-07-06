"""SQLAlchemy models for Governance bridge."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.database import Base, get_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GovernanceConfigRow(Base):
    __tablename__ = "governance_config"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_vault_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    instance_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reporting_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consecutive_failures: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    vault_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class GovernanceEventQueueRow(Base):
    __tablename__ = "governance_event_queue"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class GovernancePolicyRow(Base):
    __tablename__ = "governance_policies"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_type: Mapped[str] = mapped_column(Text, nullable=False)
    policy_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


async def ensure_governance_tables() -> None:
    factory = get_session_factory()
    if factory is None:
        return
    from keprix.database import get_engine

    engine = get_engine()
    if engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[
            GovernanceConfigRow.__table__,
            GovernanceEventQueueRow.__table__,
            GovernancePolicyRow.__table__,
        ])
