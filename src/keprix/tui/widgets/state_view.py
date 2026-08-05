"""Reusable TUI state view widget."""

from __future__ import annotations

from textual.widgets import Static

from keprix.tui.command_center.states import TuiStateView, render_tui_state


class StateView(Static):
    DEFAULT_CSS = """
    StateView {
        height: auto;
        padding: 1 2;
        border: solid $primary;
        color: $text;
    }
    """

    def update_state(self, state: TuiStateView) -> None:
        self.update(render_tui_state(state))


__all__ = ["StateView"]
