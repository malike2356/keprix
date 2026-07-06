"""Prompt injection heuristics (log-only for self-hosted CE)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PromptGuardResult:
    suspicious: bool
    patterns: list[str]
    confidence: float


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
    return PromptGuardResult(True, matched, confidence)
