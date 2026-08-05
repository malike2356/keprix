"""Terminal startup probe and degradation policy."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.tui.terminal_capabilities import TerminalCapabilities, get_terminal_capabilities


@dataclass(frozen=True)
class TerminalStartupProfile:
    capabilities: TerminalCapabilities
    simplified_ui: bool
    notes: tuple[str, ...]


def probe_terminal_startup() -> TerminalStartupProfile:
    caps = get_terminal_capabilities()
    notes: list[str] = []
    simplified = False
    if caps.is_termux:
        simplified = True
        notes.append("Termux mode: alternate screen and mouse are disabled")
    if not caps.truecolor:
        notes.append("Using reduced color mode")
    if not caps.osc52:
        notes.append("Terminal clipboard falls back to system commands")
    return TerminalStartupProfile(capabilities=caps, simplified_ui=simplified, notes=tuple(notes))

