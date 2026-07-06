"""Shared adapter helpers."""

from __future__ import annotations


def flatten_conversation(conv: dict) -> str:
    messages = conv.get("messages", [])
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        text = msg.get("content", "")
        if isinstance(text, list):
            text = " ".join(part.get("text", "") for part in text if isinstance(part, dict))
        lines.append(f"{role}: {text}")
    return "\n".join(lines)
