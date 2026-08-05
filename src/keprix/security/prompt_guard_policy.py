"""Policy helpers for prompt guard enforcement."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from keprix.security.prompt_guard import PromptGuardResult, analyze_prompt


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def prompt_guard_mode() -> str:
    mode = os.getenv("KEPRIX_PROMPT_GUARD_MODE", "quarantine").strip().lower()
    if mode not in {"log", "quarantine", "block"}:
        return "quarantine"
    return mode


def prompt_guard_block_threshold() -> float:
    return max(0.0, min(1.0, _env_float("KEPRIX_PROMPT_GUARD_BLOCK_THRESHOLD", 0.5)))


@dataclass(slots=True)
class PromptGuardDecision:
    allowed: bool
    mode: str
    confidence: float
    patterns: list[str] = field(default_factory=list)
    action: str = "allow"
    quarantined: bool = False
    blocked: bool = False
    sanitized_text: str | None = None
    reason: str | None = None

    def to_event(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "mode": self.mode,
            "confidence": self.confidence,
            "patterns": list(self.patterns),
            "action": self.action,
            "quarantined": self.quarantined,
            "blocked": self.blocked,
            "reason": self.reason,
        }


def quarantine_text(text: str, *, source: str, patterns: list[str] | None = None, confidence: float = 0.0) -> str:
    clean = text.strip()
    if not clean:
        return ""
    prefix = [
        f"[QUARANTINED {source}]",
        f"confidence={confidence:.2f}",
    ]
    if patterns:
        prefix.append(f"patterns={','.join(patterns)}")
    return "\n".join(prefix + ["", clean, f"[/QUARANTINED {source}]"])


def analyze_prompt_turn(text: str, *, mode: str | None = None, threshold: float | None = None) -> PromptGuardDecision:
    result: PromptGuardResult = analyze_prompt(text)
    resolved_mode = mode or prompt_guard_mode()
    resolved_threshold = threshold if threshold is not None else prompt_guard_block_threshold()
    if not result.suspicious:
        return PromptGuardDecision(
            allowed=True,
            mode=resolved_mode,
            confidence=0.0,
            patterns=[],
            action="allow",
        )
    if result.confidence >= resolved_threshold:
        if resolved_mode == "block":
            return PromptGuardDecision(
                allowed=False,
                mode=resolved_mode,
                confidence=result.confidence,
                patterns=list(result.patterns),
                action="block",
                blocked=True,
                reason="prompt_guard_blocked",
            )
        if resolved_mode == "quarantine":
            return PromptGuardDecision(
                allowed=True,
                mode=resolved_mode,
                confidence=result.confidence,
                patterns=list(result.patterns),
                action="quarantine",
                quarantined=True,
                sanitized_text=quarantine_text(text, source="user_input", patterns=result.patterns, confidence=result.confidence),
                reason="prompt_guard_quarantined",
            )
    return PromptGuardDecision(
        allowed=True,
        mode=resolved_mode,
        confidence=result.confidence,
        patterns=list(result.patterns),
        action="allow",
        sanitized_text=text,
        reason="prompt_guard_log",
    )

