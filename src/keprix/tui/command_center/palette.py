"""Command palette model and action execution planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from keprix.tui.command_center.actions import CommandCenterAction
from keprix.tui.command_center.registry import CommandCenterRegistry

PaletteStateName = Literal["ready", "loading", "empty", "error"]
PaletteDispatchKind = Literal["insert_text", "switch_session", "switch_model", "switch_theme", "runtime_action", "open_help", "open_review", "open_file", "open_registry", "none"]


@dataclass(frozen=True)
class CommandPaletteResult:
    action: CommandCenterAction
    dispatch_kind: PaletteDispatchKind
    value: str


@dataclass
class CommandPaletteModel:
    registry: CommandCenterRegistry
    query: str = ""
    selected_index: int = 0
    limit: int = 12
    loading: bool = False
    error: str = ""

    def results(self) -> list[CommandCenterAction]:
        if self.loading or self.error:
            return []
        return self.registry.search(self.query, limit=self.limit)

    @property
    def state(self) -> PaletteStateName:
        if self.loading:
            return "loading"
        if self.error:
            return "error"
        if not self.results():
            return "empty"
        return "ready"

    def set_query(self, query: str) -> None:
        self.query = query
        self.selected_index = 0

    def move(self, step: int) -> None:
        results = self.results()
        if not results:
            self.selected_index = 0
            return
        self.selected_index = (self.selected_index + step) % len(results)

    def selected(self) -> CommandCenterAction | None:
        results = self.results()
        if not results:
            return None
        return results[max(0, min(self.selected_index, len(results) - 1))]

    def dispatch_selected(self) -> CommandPaletteResult | None:
        action = self.selected()
        if action is None or action.disabled:
            return None
        return dispatch_for_action(action)


def dispatch_for_action(action: CommandCenterAction) -> CommandPaletteResult:
    if action.kind == "slash":
        return CommandPaletteResult(action, "insert_text", f"{action.value or action.title} ")
    if action.kind == "session":
        return CommandPaletteResult(action, "switch_session", action.value)
    if action.kind == "model":
        return CommandPaletteResult(action, "switch_model", action.value)
    if action.kind == "runtime":
        return CommandPaletteResult(action, "runtime_action", action.value)
    if action.kind == "ui" and action.id.startswith("theme:"):
        return CommandPaletteResult(action, "switch_theme", action.value)
    if action.kind == "ui" and action.value == "review":
        return CommandPaletteResult(action, "open_review", action.value)
    if action.kind == "help":
        return CommandPaletteResult(action, "open_help", action.value)
    if action.kind == "file":
        return CommandPaletteResult(action, "open_file", action.value)
    if action.kind in {"skill", "plugin"}:
        return CommandPaletteResult(action, "open_registry", action.value)
    return CommandPaletteResult(action, "none", action.value)


def palette_status_line(model: CommandPaletteModel) -> str:
    state = model.state
    if state == "loading":
        return "Loading actions..."
    if state == "error":
        return model.error or "Command palette unavailable."
    if state == "empty":
        return "No matching actions."
    return f"{len(model.results())} actions"


__all__ = [
    "CommandPaletteModel",
    "CommandPaletteResult",
    "dispatch_for_action",
    "palette_status_line",
]
