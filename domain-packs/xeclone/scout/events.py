"""Scout event emission with hashes and redacted metadata."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

_LOCK = threading.RLock()
_EVENTS: list[dict[str, Any]] = []


def reset_scout() -> None:
    with _LOCK:
        _EVENTS.clear()


def emit_scout_event(event_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
    # Redact any accidental secret-like fields
    redacted = {k: v for k, v in metadata.items() if "token" not in k.lower() and "secret" not in k.lower()}
    row = {
        "event_id": f"scout_{uuid.uuid4().hex[:12]}",
        "type": event_type,
        "metadata": redacted,
        "at": time.time(),
    }
    with _LOCK:
        _EVENTS.append(row)
    return dict(row)


def list_events() -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(e) for e in _EVENTS]
