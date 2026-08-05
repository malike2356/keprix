"""Inline tool call progress display for keprix TUI.

Shows live tool call status during streaming: tool name, status badge
(running/done/error), and result preview.  Matches Hermes's inline
tool progress pattern in streamingAssistant.tsx.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ToolStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ToolProgress:
    """Tracks a single tool call's progress."""

    tool_name: str
    tool_call_id: str = ""
    status: ToolStatus = ToolStatus.RUNNING
    message: str = ""
    result_preview: str = ""
    started_at: float = 0.0

    def complete(self, result_preview: str = "") -> None:
        self.status = ToolStatus.COMPLETED
        self.result_preview = result_preview[:200]  # Truncate long results

    def fail(self, error_message: str = "") -> None:
        self.status = ToolStatus.ERROR
        self.message = error_message[:200]

    def render(self) -> str:
        """Render a single-line tool progress indicator."""
        badge = _status_badge(self.status)
        msg = self.message if self.message else self.result_preview
        if msg:
            return f"[dim]{badge} {self.tool_name}:[/] {msg}"
        return f"[dim]{badge} {self.tool_name}[/]"


@dataclass
class ToolProgressTracker:
    """Tracks all tool calls in the current turn."""

    tools: list[ToolProgress] = field(default_factory=list)

    def start_tool(self, tool_name: str, tool_call_id: str = "") -> ToolProgress:
        tp = ToolProgress(tool_name=tool_name, tool_call_id=tool_call_id)
        import time
        tp.started_at = time.monotonic()
        self.tools.append(tp)
        return tp

    def complete_tool(self, tool_call_id: str, result_preview: str = "") -> None:
        for tp in self.tools:
            if tp.tool_call_id == tool_call_id:
                tp.complete(result_preview)

    def fail_tool(self, tool_call_id: str, error: str = "") -> None:
        for tp in self.tools:
            if tp.tool_call_id == tool_call_id:
                tp.fail(error)

    def running_tools(self) -> list[ToolProgress]:
        return [t for t in self.tools if t.status == ToolStatus.RUNNING]

    def any_running(self) -> bool:
        return any(t.status == ToolStatus.RUNNING for t in self.tools)

    def render_all(self) -> str:
        """Render all tool progress indicators."""
        lines = []
        for tp in self.tools:
            rendered = tp.render()
            if rendered.strip():
                lines.append(rendered)
        return "\n".join(lines)


def _status_badge(status: ToolStatus) -> str:
    if status == ToolStatus.RUNNING:
        return "[yellow]running[/]"
    if status == ToolStatus.COMPLETED:
        return "[green]done[/]"
    return "[red]error[/]"
