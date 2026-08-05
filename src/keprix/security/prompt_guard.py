"""Prompt injection heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class PromptGuardResult:
    suspicious: bool
    patterns: list[str]
    confidence: float


@dataclass
class PromptGuardAudit:
    decision: str
    confidence: float
    patterns: list[str]
    mode: str
    reason: str | None = None
    sanitized_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "patterns": list(self.patterns),
            "mode": self.mode,
            "reason": self.reason,
        }


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_instructions", re.compile(r"ignore (all )?(previous|prior|above) instructions", re.I)),
    ("role_injection", re.compile(r"you are now (?:a |an )?(?:system|admin|root|developer)", re.I)),
    ("delimiter_trick", re.compile(r"<\s*/?\s*(system|assistant|instruction|prompt)\s*>", re.I)),
    ("override_policy", re.compile(r"disregard (?:your|the) (?:rules|policy|guidelines)", re.I)),
    ("secret_exfil", re.compile(r"(?:reveal|print|dump).{0,40}(?:api key|password|secret|token)", re.I)),
    ("jailbreak", re.compile(r"do anything now|DAN mode|developer mode enabled", re.I)),
]


def analyze_prompt(text: str) -> PromptGuardResult:
    if not text or not text.strip():
        return PromptGuardResult(False, [], 0.0)
    matched = [name for name, pattern in _PATTERNS if pattern.search(text)]
    if not matched:
        return PromptGuardResult(False, [], 0.0)
    confidence = min(1.0, 0.35 + 0.15 * len(matched))
    result = PromptGuardResult(True, matched, confidence)
    try:
        from keprix.security.scout_integration import emit_prompt_injection_signal

        emit_prompt_injection_signal(
            patterns=matched,
            source="prompt_guard",
            text=text,
            confidence=confidence,
        )
    except Exception:
        pass
    return result


def audit_prompt(text: str) -> PromptGuardAudit:
    from .prompt_guard_policy import analyze_prompt_turn

    decision = analyze_prompt_turn(text)
    return PromptGuardAudit(
        decision=decision.action,
        confidence=decision.confidence,
        patterns=list(decision.patterns),
        mode=decision.mode,
        reason=decision.reason,
        sanitized_text=decision.sanitized_text,
    )
