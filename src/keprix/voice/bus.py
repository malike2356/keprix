"""In-process event bus for voicewake gateway broadcasts."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

EventCallback = Callable[[dict[str, Any]], None]

_lock = threading.Lock()
_subscribers: list[EventCallback] = []
_nodes: dict[str, dict[str, Any]] = {}


def subscribe(callback: EventCallback) -> Callable[[], None]:
    with _lock:
        _subscribers.append(callback)

    def unsubscribe() -> None:
        with _lock:
            if callback in _subscribers:
                _subscribers.remove(callback)

    return unsubscribe


def broadcast(payload: dict[str, Any]) -> None:
    with _lock:
        listeners = list(_subscribers)
    for listener in listeners:
        try:
            listener(payload)
        except Exception:
            continue


@dataclass
class NodeWakeStatus:
    node_id: str
    platform: str
    wake_enabled: bool
    permission_granted: bool
    last_seen_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "platform": self.platform,
            "wake_enabled": self.wake_enabled,
            "permission_granted": self.permission_granted,
            "last_seen_at": self.last_seen_at,
            "wake_detection_available": self.platform in {"desktop", "mobile"},
        }


def register_node_status(
    node_id: str,
    *,
    platform: str,
    wake_enabled: bool,
    permission_granted: bool,
) -> None:
    with _lock:
        _nodes[node_id] = NodeWakeStatus(
            node_id=node_id,
            platform=platform,
            wake_enabled=wake_enabled,
            permission_granted=permission_granted,
        ).to_dict()


def list_node_statuses() -> list[dict[str, Any]]:
    with _lock:
        return list(_nodes.values())


def clear_nodes_for_tests() -> None:
    with _lock:
        _nodes.clear()
        _subscribers.clear()
