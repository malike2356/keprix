"""Lifecycle hooks for crews and flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


HookCallable = Callable[[dict[str, Any]], None]


@dataclass(slots=True)
class HookEvent:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


class HookManager:
    def __init__(self) -> None:
        self._hooks: dict[str, list[HookCallable]] = {}
        self.events: list[HookEvent] = []

    def register(self, event_type: str, hook: HookCallable) -> None:
        self._hooks.setdefault(event_type, []).append(hook)

    def emit(self, event_type: str, **payload: Any) -> None:
        event = HookEvent(event_type=event_type, payload=dict(payload))
        self.events.append(event)
        for hook in self._hooks.get(event_type, []):
            hook(dict(payload))

    def feed_scout(self, scout_sink: HookCallable | None, event_type: str, **payload: Any) -> None:
        self.emit(event_type, **payload)
        if scout_sink:
            scout_sink({"event_type": event_type, **payload})
