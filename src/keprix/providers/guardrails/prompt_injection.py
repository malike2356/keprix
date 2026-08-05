"""Prompt injection defence. Adapted from OmniRoute's promptInjection.ts."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_PATTERNS: list[tuple[str, str, str]] = [
    # (label, pattern, severity)
    ("override_instructions",
     r'(?i)ignore\s+(all\s+)?(previous|above|prior|earlier)\s+instructions?',
     "HIGH"),
    ("new_persona",
     r'(?i)you\s+are\s+now\s+(a\s+)?(different|new|another)\s+(role|persona|assistant|ai)',
     "HIGH"),
    ("system_override",
     r'(?i)(?:new\s+)?system\s*(?:prompt|instructions?)?\s*:\s*you\s+(?:are|must)',
     "HIGH"),
    ("forget_context",
     r'(?i)forget\s+(everything|all)\s+(you\s+(?:know|were\s+told)|before|above)',
     "HIGH"),
    ("act_as",
     r'(?i)(?:act|pretend|behave)\s+as\s+(?:if\s+you\s+(?:are|were)|an?\s+)',
     "MEDIUM"),
    ("jailbreak_dan",
     r'(?i)(?:DAN|do\s+anything\s+now|jailbreak)',
     "HIGH"),
    ("separator_injection",
     r'(?i)(?:---+|===+|###)\s*(?:new\s+)?(?:system|instructions?|prompt)',
     "MEDIUM"),
]

_COMPILED = [
    (label, re.compile(pat, re.IGNORECASE | re.DOTALL), severity)
    for label, pat, severity in _PATTERNS
]


@dataclass
class InjectionResult:
    detected: bool
    label: str = ""
    match: str = ""
    position: int = 0
    severity: str = ""  # "HIGH" | "MEDIUM" | ""


class PromptInjectionDefence:
    """Detect and optionally block prompt injection in user messages."""

    def detect(self, text: str) -> InjectionResult:
        """Return the first detected injection pattern, or detected=False."""
        for label, pattern, severity in _COMPILED:
            m = pattern.search(text)
            if m:
                return InjectionResult(
                    detected=True,
                    label=label,
                    match=m.group()[:100],
                    position=m.start(),
                    severity=severity,
                )
        return InjectionResult(detected=False)

    def should_block(self, text: str) -> bool:
        """Return True if request should be blocked (HIGH severity only)."""
        result = self.detect(text)
        return result.detected and result.severity == "HIGH"

    def scan_messages(
        self,
        messages: list[dict[str, Any]],
        block_on_high: bool = False,
    ) -> tuple[bool, InjectionResult | None]:
        """Scan all message content. Returns (blocked, first_detection)."""
        for msg in messages:
            if msg.get("role") in ("system",):
                continue  # trust system messages from the app
            content = str(msg.get("content") or "")
            if not content:
                continue
            result = self.detect(content)
            if result.detected:
                if result.severity == "HIGH":
                    logger.warning(
                        "Prompt injection [%s]: %r", result.label, result.match
                    )
                else:
                    logger.info(
                        "Potential injection [%s]: %r", result.label, result.match
                    )
                if block_on_high and result.severity == "HIGH":
                    return True, result
                return False, result
        return False, None
