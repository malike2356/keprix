"""Live runtime timeline model and renderer."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from keprix.tui.runtime_events import now_monotonic

TimelineKind = Literal[
    "turn",
    "stream",
    "model",
    "transport",
    "tool",
    "subagent",
    "approval",
    "clarify",
    "api",
    "usage",
    "interrupt",
    "queue",
    "error",
]


@dataclass(frozen=True)
class RuntimeTimelineEvent:
    kind: TimelineKind
    label: str
    detail: str = ""
    status: str = ""
    created_at: float = field(default_factory=now_monotonic)


@dataclass
class RuntimeTimeline:
    max_items: int = 200
    events: list[RuntimeTimelineEvent] = field(default_factory=list)

    def add(self, event: RuntimeTimelineEvent) -> None:
        self.events.append(event)
        self.events[:] = self.events[-self.max_items :]

    def compact_events(self, *, limit: int = 12) -> list[RuntimeTimelineEvent]:
        if len(self.events) <= limit:
            return list(self.events)
        head = self.events[:3]
        tail = self.events[-(limit - 4) :]
        hidden = len(self.events) - len(head) - len(tail)
        summary = RuntimeTimelineEvent("turn", f"{hidden} earlier runtime events", status="summary")
        return [*head, summary, *tail]

    def summary_counts(self) -> dict[str, int]:
        return dict(Counter(event.kind for event in self.events))


def render_runtime_timeline(timeline: RuntimeTimeline, *, limit: int = 12) -> str:
    events = timeline.compact_events(limit=limit)
    if not events:
        return "Runtime timeline\n- idle"
    lines = ["Runtime timeline"]
    for event in events:
        status = f" [{event.status}]" if event.status else ""
        detail = f" - {event.detail}" if event.detail else ""
        lines.append(f"- {event.kind}: {event.label}{status}{detail}")
    return "\n".join(lines)


__all__ = ["RuntimeTimeline", "RuntimeTimelineEvent", "render_runtime_timeline"]
