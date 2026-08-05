"""Session map sidebar widget."""

from __future__ import annotations

from textual.widgets import Static

from keprix.tui.sessions.map import SessionMapNode, render_session_map


class SessionMapWidget(Static):
    DEFAULT_CSS = """
    SessionMapWidget {
        height: auto;
        max-height: 8;
        padding: 1 0 0 0;
        color: $text-muted;
    }
    """

    def update_map(
        self,
        nodes: list[SessionMapNode],
        *,
        selected_id: str = "",
        width: int = 34,
    ) -> None:
        self.update(render_session_map(nodes, selected_id=selected_id, width=width))
