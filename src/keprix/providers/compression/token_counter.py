"""Token counting utilities. Uses tiktoken when available, falls back to word estimate."""

from __future__ import annotations

from typing import Any


def count_tokens(text: str | list | dict | Any) -> int:
    """Estimate token count for text or a message list."""
    if isinstance(text, list):
        return sum(count_tokens(item) for item in text)
    if isinstance(text, dict):
        content = text.get("content", "")
        if isinstance(content, list):
            return sum(count_tokens(c) for c in content)
        return count_tokens(str(content or ""))
    if not isinstance(text, str):
        text = str(text)
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))
    except Exception:
        return estimate_tokens(text)


def estimate_tokens(text: str) -> int:
    """Fast approximation: ~4 chars per token (GPT-4 average)."""
    return max(1, len(text) // 4)
