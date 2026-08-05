"""Quarantine wrappers for untrusted context before it reaches the model."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.security.prompt_guard_policy import quarantine_text


@dataclass(slots=True)
class QuarantinedContext:
    source: str
    content: str
    confidence: float = 0.0
    patterns: list[str] = field(default_factory=list)
    trust: str = "quarantined"

    def to_prompt_block(self) -> str:
        return quarantine_text(
            self.content,
            source=self.source,
            patterns=self.patterns,
            confidence=self.confidence,
        )


def wrap_context(content: str, *, source: str, confidence: float = 0.0, patterns: list[str] | None = None) -> QuarantinedContext:
    return QuarantinedContext(
        source=source,
        content=content,
        confidence=confidence,
        patterns=list(patterns or []),
    )

