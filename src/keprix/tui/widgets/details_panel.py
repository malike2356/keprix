"""Details panel data model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MessageDetails:
    model: str = ""
    tokens: int = 0
    latency_ms: int = 0
    tool_trace: list[str] = field(default_factory=list)

    def render(self) -> str:
        rows = [f"Model: {self.model or '-'}", f"Tokens: {self.tokens}", f"Latency: {self.latency_ms} ms"]
        rows.extend(f"Tool: {tool}" for tool in self.tool_trace)
        return "\n".join(rows)

