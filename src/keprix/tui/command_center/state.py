"""Command Center state models."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

SurfaceName = Literal[
    "chat",
    "cockpit",
    "palette",
    "runtime_timeline",
    "session_map",
    "review",
    "help",
]

FocusTarget = Literal["input", "transcript", "sidebar", "overlay", "status", "timeline"]
RuntimeStatus = Literal["idle", "busy", "offline", "error", "reconnecting"]
TransportMode = Literal["in_process", "websocket", "http", "unknown"]


@dataclass(frozen=True)
class CommandCenterState:
    active_surface: SurfaceName = "chat"
    selected_action_id: str = ""
    focus_target: FocusTarget = "input"
    transport_mode: TransportMode = "unknown"
    current_session_id: str = ""
    queue_depth: int = 0
    runtime_status: RuntimeStatus = "idle"
    theme: str = "Keprix Matrix"

    def with_updates(self, **changes: object) -> "CommandCenterState":
        return replace(self, **changes)

    @property
    def overlay_open(self) -> bool:
        return self.active_surface in {"palette", "review", "help"}


__all__ = ["CommandCenterState", "FocusTarget", "RuntimeStatus", "SurfaceName", "TransportMode"]
