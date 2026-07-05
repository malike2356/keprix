"""Core agent types and protocols.

These are the contracts the engine, tools, and providers all talk to.
Cursor builds concrete implementations against these interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Protocol, runtime_checkable


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: MessageRole
    content: str | list[dict[str, Any]]
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AgentTurn:
    """One complete agent reasoning turn: content blocks + any tool calls."""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "end_turn"


@dataclass
class StreamChunk:
    """One chunk from a streaming agent response."""
    text: str = ""
    tool_call: ToolCall | None = None
    is_final: bool = False


@dataclass
class AgentContext:
    """Full execution context passed through the agent loop."""
    session_id: str
    messages: list[Message] = field(default_factory=list)
    model: str = ""
    system_prompt: str = ""
    max_iterations: int = 20
    iteration: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AgentRunner(Protocol):
    """Protocol for any object that can run an agent turn."""

    async def run(self, context: AgentContext) -> AgentTurn: ...

    async def stream(self, context: AgentContext) -> AsyncIterator[StreamChunk]: ...
