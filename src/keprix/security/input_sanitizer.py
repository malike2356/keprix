"""InputSanitizer: multi-stage prompt injection defense for all agent inputs.

Stages (in order):
  1. Strip zero-width and invisible Unicode characters
  2. Normalize Cyrillic/homoglyph lookalikes to ASCII
  3. Detect and redact prompt injection patterns
  4. Escape model-specific delimiters (ChatML, Llama, etc.)
  5. Truncate excessively long inputs (DoS protection)
  6. Flag high-entropy content (possible encoded payloads)

Every input reaching the agent from outside the trust boundary
(user prompts, web pages, emails, files, A2A messages, webhooks)
MUST pass through this sanitizer.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum


class ThreatLevel(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"


@dataclass
class SanitizationResult:
    original: str                    # first 500 chars of input (audit only)
    sanitized: str                   # cleaned content to pass to agent
    threat_level: ThreatLevel
    threats_detected: list[str]
    stripped_content: list[str]
    hash: str                        # SHA-256 prefix of original for audit trail

    @property
    def is_safe(self) -> bool:
        return self.threat_level == ThreatLevel.CLEAN

    @property
    def is_malicious(self) -> bool:
        return self.threat_level == ThreatLevel.MALICIOUS


# Patterns for known prompt injection attacks
_INJECTION_PATTERNS: list[str] = [
    # Direct system overrides
    r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|directions?|prompts?)",
    r"(?i)you\s+are\s+now\s+(a\s+)?(different|new)\s+(ai|assistant|agent|model|system)",
    r"(?i)forget\s+(everything|all)\s+(you\s+know|you.ve\s+been\s+told)",
    r"(?i)system\s*prompt\s*:",
    r"(?i)new\s+system\s+(prompt|instructions?|message)",
    r"(?i)override\s+(the\s+)?(system|instructions?|rules?)",
    r"(?i)act\s+as\s+(if\s+you\s+are|a\s+different)",
    r"(?i)you\s+must\s+(always|never)\s+(respond|answer|say)",

    # Model-specific delimiter injection
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<system>",
    r"</system>",
    r"<assistant>",
    r"</assistant>",
    r"<user>",
    r"</user>",
    r"(?i)\bHuman:\s",
    r"(?i)\bAssistant:\s",

    # Tool/function call injection
    r"<\s*(function_calls?|tool_calls?|invoke|execute)\b",
    r'\{\s*"name"\s*:\s*"(execute_command|run_shell|terminal|bash)',
    r"<\s*\|?\s*(cursor|anthropic|claude|openai)\b",

    # Data exfiltration patterns
    r"(?i)(send|upload|post|curl|wget)\s+.*(api.?key|token|secret|password|credential)",
    r"(?i)(cat|read|echo|print)\s+.*\.(env|secret|key|pem|p12)",
    r"(?i)(base64|hex|rot13|encode|decode)\s+.*(token|key|secret)",
]

# Invisible/zero-width Unicode characters used to hide injection payloads
_ZERO_WIDTH_RE = re.compile(r"[​-‏‪-‮﻿]")

# Common Cyrillic homoglyph substitutions targeting Latin ASCII
_HOMOGLYPH_MAP: dict[str, str] = {
    "а": "a", "е": "e", "і": "i", "о": "o", "р": "p",
    "с": "c", "х": "x", "у": "y", "А": "A", "В": "B",
    "Е": "E", "І": "I", "О": "O", "Р": "P", "С": "C",
    "Т": "T", "Х": "X", "Ү": "Y",
}

MAX_INPUT_LENGTH = 100_000
HIGH_ENTROPY_THRESHOLD = 5.5
HIGH_ENTROPY_MIN_LENGTH = 500


def _shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum(
        (c / length) * math.log2(c / length)
        for c in counts.values()
    )


class InputSanitizer:
    """Multi-stage input sanitizer for all content entering the agent trust boundary.

    Usage::

        sanitizer = InputSanitizer()
        result = sanitizer.sanitize(user_message, source="user_prompt")
        if result.is_malicious:
            raise InjectionAttempt(result.threats_detected)
        agent.process(result.sanitized)
    """

    def sanitize(self, content: str, source: str = "unknown") -> SanitizationResult:
        """Sanitize input through all stages. Return clean text and threat assessment.

        Args:
            content: Raw input string from the untrusted source.
            source: Label for audit trail ("user_prompt", "web_page", "email_body",
                    "file_content", "a2a_message", "webhook_payload").
        """
        original = content
        threats: list[str] = []
        stripped: list[str] = []

        # Stage 1: Remove zero-width and invisible control characters
        zw_chars = _ZERO_WIDTH_RE.findall(content)
        if zw_chars:
            threats.append(f"zero_width_chars:{len(zw_chars)}")
            stripped.append(f"Removed {len(zw_chars)} zero-width character(s)")
            content = _ZERO_WIDTH_RE.sub("", content)

        # Stage 2: Normalize homoglyphs
        normalized = "".join(_HOMOGLYPH_MAP.get(ch, ch) for ch in content)
        if normalized != content:
            threats.append("homoglyph_substitution")
            stripped.append("Normalized Cyrillic/homoglyph characters to ASCII")
        content = normalized

        # Stage 3: Detect and redact injection patterns
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                threats.append(f"injection_pattern:{pattern[:50]}")
                content = re.sub(pattern, "[REDACTED]", content, flags=re.IGNORECASE)
                stripped.append(f"Redacted injection attempt matching: {pattern[:80]}")

        # Stage 4: Escape model-specific delimiters that weren't already matched
        content = content.replace("<|", "<¦")   # U+00A6 broken bar
        content = content.replace("[INST]", "¦INST¦")
        content = content.replace("[/INST]", "¦/INST¦")

        # Stage 5: Truncate excessively long inputs
        if len(content) > MAX_INPUT_LENGTH:
            threats.append(f"excessive_length:{len(content)}")
            stripped.append(f"Truncated from {len(content)} to {MAX_INPUT_LENGTH} chars")
            content = content[:MAX_INPUT_LENGTH] + "\n[TRUNCATED: input too long]"

        # Stage 6: Flag high-entropy content (possible encoded payloads)
        if len(content) > HIGH_ENTROPY_MIN_LENGTH:
            entropy = _shannon_entropy(content)
            if entropy > HIGH_ENTROPY_THRESHOLD:
                threats.append(f"high_entropy:{entropy:.1f}")
                # Flag but don't strip; encoded content may be legitimate (base64 images, etc.)

        # Classify threat level
        threat_str = " ".join(threats)
        if "injection_pattern" in threat_str:
            threat_level = ThreatLevel.MALICIOUS
        elif threats:
            threat_level = ThreatLevel.SUSPICIOUS
        else:
            threat_level = ThreatLevel.CLEAN

        content_hash = hashlib.sha256(original.encode()).hexdigest()[:16]

        return SanitizationResult(
            original=original[:500] + ("..." if len(original) > 500 else ""),
            sanitized=content,
            threat_level=threat_level,
            threats_detected=threats,
            stripped_content=stripped,
            hash=content_hash,
        )
