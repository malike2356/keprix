"""In-process event bus for upgrade notifications."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

_listeners: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
_lock = threading.Lock()


def on_event(event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
    """Register a listener for an event type."""
    with _lock:
        _listeners.setdefault(event_type, []).append(callback)


def emit_update_event(event_type: str, data: dict[str, Any]) -> None:
    """Emit an event to all registered listeners."""
    with _lock:
        callbacks = list(_listeners.get(event_type, []))
    for callback in callbacks:
        try:
            callback(data)
        except Exception:
            continue


def clear_listeners(event_type: str | None = None) -> None:
    """Clear listeners (used in tests)."""
    with _lock:
        if event_type is None:
            _listeners.clear()
        else:
            _listeners.pop(event_type, None)
