"""Workspace cockpit widget."""

from __future__ import annotations

from textual.widgets import Static

from keprix.tui.command_center.cockpit import WorkspaceCockpitState, render_workspace_cockpit


class WorkspaceCockpit(Static):
    """Compact first-screen cockpit for empty TUI sessions."""

    DEFAULT_CSS = """
    WorkspaceCockpit {
        background: #000000;
        color: #00CC33;
        border: solid #003B00;
        padding: 1 2;
        margin: 1 2 0 2;
        height: auto;
    }
    """

    def update_state(self, state: WorkspaceCockpitState, *, visible: bool = True) -> None:
        if not visible:
            self.update("")
            self.display = False
            return
        self.display = True
        self.update(render_workspace_cockpit(state))


__all__ = ["WorkspaceCockpit"]
