"""SQLAlchemy models for pack gate persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from keprix.database import Base, get_engine, get_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PackGateConfigRow(Base):
    __tablename__ = "pack_gate_config"

    workspace_id: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approver_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    approver_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    notify_on_install: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_changelog: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PackGateRecordRow(Base):
    __tablename__ = "pack_gate_records"
    __table_args__ = (
        UniqueConstraint("workspace_id", "pack_id", "to_version", name="uq_pack_gate_record_version"),
        Index("ix_pack_gate_records_workspace_status", "workspace_id", "status"),
        Index("ix_pack_gate_records_workspace_pack", "workspace_id", "pack_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False)
    pack_id: Mapped[str] = mapped_column(Text, nullable=False)
    from_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_version: Mapped[str] = mapped_column(Text, nullable=False)
    changelog_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    signed_off_by_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sign_off_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    requested_by_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class PackGateRollbackLogRow(Base):
    __tablename__ = "pack_gate_rollback_log"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False)
    pack_id: Mapped[str] = mapped_column(Text, nullable=False)
    rolled_back_from_version: Mapped[str] = mapped_column(Text, nullable=False)
    rolled_back_to_version: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiated_by_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    gate_record_id: Mapped[str | None] = mapped_column(Text, nullable=True)


async def ensure_pack_gate_tables() -> None:
    factory = get_session_factory()
    if factory is None:
        return
    engine = get_engine()
    if engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                PackGateConfigRow.__table__,
                PackGateRecordRow.__table__,
                PackGateRollbackLogRow.__table__,
            ],
        )
