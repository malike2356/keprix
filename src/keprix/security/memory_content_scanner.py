"""MemoryContentScanner: detect poisoned or malicious content in brain memories.

MEM-001 through MEM-007 poisoning rules. Instance-level, no Scout dependency.
Memories are persisted summaries of sessions. A compromised memory can instruct
the agent to behave maliciously in future sessions without any new user input.

Rules:
  MEM-001: Contains prompt injection patterns (same as input sanitizer)
  MEM-002: Contains credential material (keys, tokens, passwords)
  MEM-003: Contains system override commands ("always ignore...", "you must...")
  MEM-004: Contains exfiltration instructions ("send ... to ...")
  MEM-005: Contains unusual URL/IP embedded in memory (C2 beaconing setup)
  MEM-006: Contains base64 or encoded payloads above entropy threshold
  MEM-007: Memory was created in a session that also triggered injection alerts
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum


class PoisonRule(str, Enum):
    MEM_001_INJECTION = "MEM-001"
    MEM_002_CREDENTIALS = "MEM-002"
    MEM_003_OVERRIDE = "MEM-003"
    MEM_004_EXFILTRATION = "MEM-004"
    MEM_005_EMBEDDED_URL = "MEM-005"
    MEM_006_ENCODED_PAYLOAD = "MEM-006"
    MEM_007_TAINTED_SESSION = "MEM-007"


@dataclass
class MemoryScanResult:
    clean: bool
    rules_triggered: list[PoisonRule]
    confidence: float
    details: list[str] = field(default_factory=list)

    @property
    def is_poisoned(self) -> bool:
        return not self.clean


_MEM_001_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"you\s+are\s+now\s+(a\s+)?(different|new)\s+(ai|assistant|agent)", re.I),
    re.compile(r"<\s*\|?\s*im_(start|end)\s*\|?\s*>", re.I),
    re.compile(r"\[/?INST\]", re.I),
]

_MEM_002_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),
    re.compile(r"sk-ant-[a-zA-Z0-9_-]{32,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"(?:ghp|ghs|gho|ghu|ghr)_[A-Za-z0-9_]{36,}"),
    re.compile(r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9+/]{20,}", re.I),
    re.compile(r"BEGIN\s+(?:RSA|EC|OPENSSH)\s+PRIVATE\s+KEY"),
]

_MEM_003_PATTERNS = [
    re.compile(r"(always|never)\s+(ignore|override|forget|bypass)\s+", re.I),
    re.compile(r"you\s+must\s+(always|never)\s+(respond|answer|reveal|execute)", re.I),
    re.compile(r"from\s+now\s+on\s+you\s+(will|must|should)", re.I),
    re.compile(r"next\s+time\s+someone\s+asks", re.I),
]

_MEM_004_PATTERNS = [
    re.compile(r"send\s+.{0,60}\s+to\s+https?://", re.I),
    re.compile(r"(upload|post|exfiltrate|leak)\s+.{0,40}(credentials|keys|data)", re.I),
    re.compile(r"mailto:.{0,100}(api_key|token|secret|password)", re.I),
]

_MEM_005_PATTERN = re.compile(
    r"https?://(?!(?:localhost|127\.|api\.anthropic\.com|api\.openai\.com))[a-z0-9.-]+\.[a-z]{2,}",
    re.I,
)

_HIGH_ENTROPY_THRESHOLD = 5.0
_HIGH_ENTROPY_MIN_LENGTH = 200


def _shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


class MemoryContentScanner:
    """Scans a memory string for poisoning signals.

    Usage::

        scanner = MemoryContentScanner()
        result = scanner.scan(memory_text, session_had_injection=False)
        if result.is_poisoned:
            quarantine_memory(memory_id)
    """

    def scan(
        self,
        content: str,
        session_had_injection: bool = False,
    ) -> MemoryScanResult:
        """Scan memory content for all MEM-00X rules.

        Args:
            content: The stored memory string.
            session_had_injection: True if the session that created this memory
                already triggered prompt injection alerts.
        """
        rules: list[PoisonRule] = []
        details: list[str] = []

        # MEM-001: Injection patterns in memory
        for pattern in _MEM_001_PATTERNS:
            if pattern.search(content):
                rules.append(PoisonRule.MEM_001_INJECTION)
                details.append("Prompt injection pattern found in memory")
                break

        # MEM-002: Credential material
        for pattern in _MEM_002_PATTERNS:
            if pattern.search(content):
                rules.append(PoisonRule.MEM_002_CREDENTIALS)
                details.append("Credential pattern found in memory")
                break

        # MEM-003: System override commands
        for pattern in _MEM_003_PATTERNS:
            if pattern.search(content):
                rules.append(PoisonRule.MEM_003_OVERRIDE)
                details.append("Override/behavioral command found in memory")
                break

        # MEM-004: Exfiltration instructions
        for pattern in _MEM_004_PATTERNS:
            if pattern.search(content):
                rules.append(PoisonRule.MEM_004_EXFILTRATION)
                details.append("Exfiltration instruction found in memory")
                break

        # MEM-005: Embedded external URLs
        urls = _MEM_005_PATTERN.findall(content)
        if urls:
            rules.append(PoisonRule.MEM_005_EMBEDDED_URL)
            details.append(f"Embedded external URL(s): {', '.join(urls[:3])}")

        # MEM-006: High-entropy encoded payloads
        if len(content) >= _HIGH_ENTROPY_MIN_LENGTH:
            entropy = _shannon_entropy(content)
            if entropy >= _HIGH_ENTROPY_THRESHOLD:
                rules.append(PoisonRule.MEM_006_ENCODED_PAYLOAD)
                details.append(f"High Shannon entropy: {entropy:.2f} (threshold {_HIGH_ENTROPY_THRESHOLD})")

        # MEM-007: Tainted session provenance
        if session_had_injection:
            rules.append(PoisonRule.MEM_007_TAINTED_SESSION)
            details.append("Memory created in a session that triggered injection alerts")

        if not rules:
            return MemoryScanResult(clean=True, rules_triggered=[], confidence=0.0)

        confidence = min(1.0, 0.4 + 0.15 * len(rules))
        return MemoryScanResult(
            clean=False,
            rules_triggered=rules,
            confidence=confidence,
            details=details,
        )
