"""Message metadata rendering."""

from __future__ import annotations


def render_message_metadata(*, model: str = "", tokens: int | None = None, latency_ms: int | None = None, tools: int = 0) -> str:
    parts: list[str] = []
    if model:
        parts.append(model)
    if tokens is not None:
        parts.append(f"{tokens} tokens")
    if latency_ms is not None:
        parts.append(f"{latency_ms} ms")
    if tools:
        parts.append(f"{tools} tools")
    return " | ".join(parts)

