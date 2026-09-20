"""Mount / unmount audit events."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LifecycleAuditEvent:
    action: str  # mount | unmount
    plugin_id: str
    when: float
    who: str = "operator"
    ok: bool = True
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_EVENTS: list[LifecycleAuditEvent] = []
_LOCK = threading.Lock()
_MAX_EVENTS = 500


def emit_lifecycle_audit(
    action: str,
    plugin_id: str,
    *,
    who: str = "operator",
    ok: bool = True,
    detail: dict[str, Any] | None = None,
) -> LifecycleAuditEvent:
    event = LifecycleAuditEvent(
        action=action,
        plugin_id=plugin_id,
        when=time.time(),
        who=who,
        ok=ok,
        detail=detail or {},
    )
    with _LOCK:
        _EVENTS.append(event)
        if len(_EVENTS) > _MAX_EVENTS:
            del _EVENTS[: len(_EVENTS) - _MAX_EVENTS]
    return event


def list_audit_events(*, limit: int = 100) -> list[dict[str, Any]]:
    with _LOCK:
        slice_ = _EVENTS[-limit:]
        return [e.to_dict() for e in slice_]


def reset_audit_for_tests() -> None:
    with _LOCK:
        _EVENTS.clear()
