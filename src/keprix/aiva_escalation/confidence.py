"""Confidence scoring heuristics for escalation (K05)."""

from __future__ import annotations

import re
from typing import Any

_UNCERTAIN = (
    r"\bi'?m not sure\b",
    r"\bi don'?t know\b",
    r"\bi cannot (?:help|answer)\b",
    r"\bunable to (?:determine|confirm|verify)\b",
    r"\bout of (?:my )?scope\b",
    r"\bneed (?:a )?human\b",
    r"\bescalat",
    r"\buncertain\b",
    r"\bmight be\b",
    r"\bpossibly\b",
    r"\bi think\b",
)


def estimate_confidence(
    *,
    assistant_text: str,
    original_input: str = "",
    explicit: float | None = None,
) -> float:
    """Return 0..1 confidence. Explicit score wins when provided."""
    if explicit is not None:
        try:
            return max(0.0, min(1.0, float(explicit)))
        except (TypeError, ValueError):
            pass

    text = (assistant_text or "").strip()
    if not text:
        return 0.2

    score = 0.85
    lower = text.lower()
    hits = sum(1 for pat in _UNCERTAIN if re.search(pat, lower))
    if hits:
        score -= min(0.55, 0.18 * hits)

    if len(text) < 40 and "?" in text:
        score -= 0.15
    if "as an ai" in lower or "language model" in lower:
        score -= 0.1

    # Very long confident answers stay high; short non-answers drop
    if len(text.split()) < 8 and hits == 0:
        score -= 0.05

    _ = original_input  # reserved for future input/output alignment
    return max(0.0, min(1.0, round(score, 3)))


def should_escalate(
    confidence: float,
    threshold: float,
    *,
    force: bool = False,
    escalation_type: str | None = None,
) -> bool:
    if force:
        return True
    if escalation_type in {"manual_request", "safety_flag", "out_of_scope"}:
        return True
    return confidence < threshold


def last_user_input(messages: list[dict[str, Any]] | None) -> str:
    for msg in reversed(messages or []):
        if not isinstance(msg, dict):
            continue
        if str(msg.get("role") or "").lower() != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""
