"""Typed message envelopes for TUI rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

MessageRole = Literal["user", "assistant", "tool_call", "tool_result", "error", "system"]
ToolStatus = Literal["running", "done", "error"]


@dataclass(frozen=True)
class ToolDisplay:
    name: str
    status: ToolStatus = "running"
    args: dict[str, Any] = field(default_factory=dict)
    result: str = ""


@dataclass(frozen=True)
class TuiMessage:
    role: MessageRole
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    model: str | None = None
    token_count: int | None = None
    latency_ms: int | None = None
    tool: ToolDisplay | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

