"""Runtime timeline widget."""

from __future__ import annotations

from textual.widgets import Static

from keprix.tui.command_center.runtime_timeline import RuntimeTimeline, render_runtime_timeline


class RuntimeTimelineWidget(Static):
    """Compact live runtime event timeline."""

    DEFAULT_CSS = """
    RuntimeTimelineWidget {
        background: #000000;
        color: #00CC33;
        border: solid #003B00;
        padding: 1 2;
        margin: 0 2 0 2;
        height: auto;
        display: none;
    }
    """

    def update_timeline(self, timeline: RuntimeTimeline, *, visible: bool = True) -> None:
        if not visible:
            self.update("")
            self.display = False
            return
        self.display = True
        self.update(render_runtime_timeline(timeline))


__all__ = ["RuntimeTimelineWidget"]
