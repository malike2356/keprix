"""Working memory context compression helpers."""

from __future__ import annotations

from typing import Any


class ContextCompressor:
    """Prune working-memory facts when approaching context limits."""

    def __init__(
        self,
        *,
        context_length: int = 128_000,
        threshold_percent: float = 0.85,
        chars_per_token: float = 4.0,
    ) -> None:
        self.context_length = context_length
        self.threshold_percent = threshold_percent
        self.chars_per_token = chars_per_token
        self.threshold_tokens = int(context_length * threshold_percent)

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / self.chars_per_token))

    def should_prune(self, memory_text: str, conversation_text: str) -> bool:
        total = self.estimate_tokens(memory_text) + self.estimate_tokens(conversation_text)
        return total >= self.threshold_tokens

    def prune_memories(self, memories: list[str], *, keep: int = 10) -> list[str]:
        if len(memories) <= keep:
            return memories
        return memories[-keep:]

    def prune_messages(self, messages: list[dict[str, Any]], *, keep: int = 20) -> list[dict[str, Any]]:
        if len(messages) <= keep:
            return messages
        head = messages[:1]
        tail = messages[-keep:]
        return head + tail
