"""Debug overlay state for TUI developer tooling."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DebugOverlayState:
    render_tree: str = ""
    events: list[str] = field(default_factory=list)
    state: dict[str, str] = field(default_factory=dict)

    def log_event(self, event: str) -> None:
        self.events.append(event)
        self.events[:] = self.events[-500:]

