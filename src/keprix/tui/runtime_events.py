"""Typed runtime events and metadata for the Keprix TUI."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

ToolRuntimeStatus = Literal["queued", "running", "done", "error", "cancelled"]
SubagentRuntimeStatus = Literal["queued", "running", "done", "error", "cancelled"]
MessageRuntimeStatus = Literal["streaming", "complete", "interrupted", "errored"]


def now_monotonic() -> float:
    return time.monotonic()


def redact_mapping(raw: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in raw.items():
        lower = str(key).lower()
        if any(secret in lower for secret in ("key", "token", "secret", "password", "cookie", "authorization")):
            redacted[str(key)] = "[redacted]"
        elif isinstance(value, dict):
            redacted[str(key)] = redact_mapping(value)
        else:
            redacted[str(key)] = value
    return redacted


@dataclass
class ToolRuntimeEvent:
    name: str
    call_id: str = ""
    status: ToolRuntimeStatus = "running"
    args: dict[str, Any] = field(default_factory=dict)
    result_preview: str = ""
    error: str = ""
    started_at: float = field(default_factory=now_monotonic)
    finished_at: float | None = None

    @property
    def elapsed_sec(self) -> float:
        end = self.finished_at or now_monotonic()
        return max(0.0, end - self.started_at)

    @property
    def safe_args(self) -> dict[str, Any]:
        return redact_mapping(self.args)


@dataclass
class SubagentRuntimeEvent:
    subagent_id: str
    label: str
    parent_id: str = ""
    status: SubagentRuntimeStatus = "running"
    preview: str = ""
    cost_hint: str = ""
    started_at: float = field(default_factory=now_monotonic)
    finished_at: float | None = None

    @property
    def elapsed_sec(self) -> float:
        end = self.finished_at or now_monotonic()
        return max(0.0, end - self.started_at)


@dataclass
class MessageRuntimeMetadata:
    message_id: str = ""
    role: str = "assistant"
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_estimate: float = 0.0
    tool_calls: int = 0
    status: MessageRuntimeStatus = "complete"
    created_at: float = field(default_factory=now_monotonic)


@dataclass
class ApiRuntimeEvent:
    request_id: str = ""
    provider: str = ""
    model: str = ""
    status: str = ""
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    request_preview: str = ""
    response_preview: str = ""
    error: str = ""


@dataclass(frozen=True)
class SkillRuntimeItem:
    name: str
    description: str = ""
    installed: bool = True
    enabled: bool = True
    source: str = ""


@dataclass(frozen=True)
class PluginRuntimeItem:
    name: str
    description: str = ""
    version: str = ""
    installed: bool = True
    enabled: bool = True
    source: str = ""

