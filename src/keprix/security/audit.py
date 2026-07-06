"""Structured security audit logging."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.config.settings import get_settings
from keprix.database import Base, get_session_factory

logger = logging.getLogger(__name__)


def hash_ip(ip: str) -> str:
    settings = get_settings()
    salt = settings.ip_hash_salt or "keprix-default-salt"
    if not ip:
        return hashlib.sha256(salt.encode("utf-8")).hexdigest()
    return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLogger:
    """Write security events to PostgreSQL when available, else application log."""

    async def log_event(
        self,
        *,
        event_type: str,
        action: str,
        result: str,
        user_id: str | None = None,
        session_id: str | None = None,
        ip: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        entry = AuditLogEntry(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            ip_hash=hash_ip(ip or ""),
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            detail=detail or {},
        )
        factory = get_session_factory()
        if factory is None:
            logger.info(
                "audit event_type=%s action=%s result=%s user_id=%s ip_hash=%s detail=%s",
                event_type,
                action,
                result,
                user_id,
                entry.ip_hash,
                detail or {},
            )
            return
        try:
            async with factory() as session:
                session.add(entry)
                await session.commit()
        except Exception as exc:
            logger.warning(
                "audit persist failed event_type=%s action=%s user_id=%s error=%s",
                event_type,
                action,
                user_id,
                exc,
            )
            logger.info(
                "audit event_type=%s action=%s result=%s user_id=%s ip_hash=%s detail=%s",
                event_type,
                action,
                result,
                user_id,
                entry.ip_hash,
                detail or {},
            )

    async def list_events(
        self,
        *,
        user_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        factory = get_session_factory()
        if factory is None:
            return []
        async with factory() as session:
            query = select(AuditLogEntry).order_by(AuditLogEntry.occurred_at.desc()).limit(limit)
            if user_id:
                query = query.where(AuditLogEntry.user_id == user_id)
            if event_type:
                query = query.where(AuditLogEntry.event_type == event_type)
            result = await session.execute(query)
            return list(result.scalars().all())


_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def _strip_secrets(data: dict[str, Any]) -> dict[str, Any]:
    redacted_keys = {"password", "master_password", "value", "secret", "token", "totp_secret"}
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in redacted_keys:
            cleaned[key] = "[REDACTED]"
        elif isinstance(value, dict):
            cleaned[key] = _strip_secrets(value)
        else:
            cleaned[key] = value
    return cleaned


async def audit_log(
    event_type: str,
    *,
    user_id: str | None = None,
    event_data: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    severity: str = "info",
) -> None:
    del ip_address, user_agent, severity
    await get_audit_logger().log_event(
        event_type=event_type,
        action=event_type,
        result="ok",
        user_id=user_id,
        detail=_strip_secrets(event_data or {}),
    )
    try:
        from keprix.governance.event_reporter import queue_audit_event

        await queue_audit_event(
            "audit_log",
            {
                "event_type": event_type,
                "user_id": user_id,
                "detail": _strip_secrets(event_data or {}),
            },
        )
    except Exception:
        pass
