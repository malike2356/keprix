"""Security event reporting for self-configuration actions."""

from __future__ import annotations

from typing import Any

from keprix.security.audit import get_audit_logger


async def report_security_event(
    event_type: str,
    severity: str,
    detail: dict[str, Any] | None = None,
) -> None:
    """Log a self-configuration security event via the audit logger."""
    logger = get_audit_logger()
    await logger.log_event(
        event_type=event_type,
        action=event_type,
        result=severity,
        detail=detail or {},
    )
