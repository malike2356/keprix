"""Local-only Command Center UI telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass(frozen=True)
class UiTelemetryEvent:
    action_id: str
    surface: str
    outcome: str = "selected"
    created_at: float = field(default_factory=time.monotonic)


class UiTelemetryBuffer:
    def __init__(self, max_items: int = 500) -> None:
        self.max_items = max_items
        self._events: list[UiTelemetryEvent] = []

    def record(self, event: UiTelemetryEvent) -> None:
        self._events.append(event)
        self._events[:] = self._events[-self.max_items :]

    def snapshot(self) -> list[UiTelemetryEvent]:
        return list(self._events)


__all__ = ["UiTelemetryBuffer", "UiTelemetryEvent"]
