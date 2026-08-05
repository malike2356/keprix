"""Command Center layout zones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LayoutZoneName = Literal[
    "cockpit",
    "transcript",
    "runtime_timeline",
    "sidebar",
    "status_bar",
    "overlay",
    "review_mode",
]


@dataclass(frozen=True)
class LayoutZone:
    name: LayoutZoneName
    purpose: str
    collapsible: bool = False
    focusable: bool = False


COMMAND_CENTER_LAYOUT_ZONES: tuple[LayoutZone, ...] = (
    LayoutZone("cockpit", "First-screen workspace cockpit and empty transcript surface", focusable=True),
    LayoutZone("transcript", "Primary chat transcript and streaming output", focusable=True),
    LayoutZone("runtime_timeline", "Live runtime events, tools, subagents, approvals, usage, and latency", collapsible=True, focusable=True),
    LayoutZone("sidebar", "Sessions, workspace context, and navigation helpers", collapsible=True, focusable=True),
    LayoutZone("status_bar", "Operational model, transport, queue, latency, token, and health signal"),
    LayoutZone("overlay", "Command palette, help, approvals, clarify, and setup surfaces", focusable=True),
    LayoutZone("review_mode", "Turn review summary for files, tools, risks, tests, and next actions", collapsible=True, focusable=True),
)


def layout_zone(name: LayoutZoneName) -> LayoutZone:
    for zone in COMMAND_CENTER_LAYOUT_ZONES:
        if zone.name == name:
            return zone
    raise KeyError(name)


__all__ = ["COMMAND_CENTER_LAYOUT_ZONES", "LayoutZone", "LayoutZoneName", "layout_zone"]
