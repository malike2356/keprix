"""Input metrics for the composer footer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InputMetrics:
    chars: int
    words: int
    estimated_tokens: int
    estimated_cost: float = 0.0


def measure_input(text: str, *, cost_per_1k_tokens: float = 0.0) -> InputMetrics:
    chars = len(text)
    words = len([word for word in text.split() if word])
    tokens = max(1, round(chars / 4)) if chars else 0
    return InputMetrics(chars=chars, words=words, estimated_tokens=tokens, estimated_cost=(tokens / 1000) * cost_per_1k_tokens)
