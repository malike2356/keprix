"""Shared scan and verdict helper for RAG and Graphiti ingest."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.security.memory_content_scanner import MemoryContentScanner, PoisonRule
from keprix.security.prompt_guard_policy import analyze_prompt_turn


@dataclass(slots=True)
class IngestVerdict:
    decision: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    trust: str = "trusted"
    preview: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"

    @property
    def quarantined(self) -> bool:
        return self.decision == "quarantine"

    @property
    def rejected(self) -> bool:
        return self.decision == "reject"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "patterns": list(self.patterns),
            "trust": self.trust,
            "preview": self.preview,
        }


def _preview(text: str, limit: int = 220) -> str:
    clean = " ".join(text.split())
    return clean[:limit]


def evaluate_ingest_text(
    text: str,
    *,
    source_type: str,
    source_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> IngestVerdict:
    metadata = metadata or {}
    normalized = str(text or "").strip()
    if not normalized:
        return IngestVerdict(decision="reject", confidence=1.0, reasons=["empty_content"], trust="rejected")

    prompt_decision = analyze_prompt_turn(normalized)
    scan = MemoryContentScanner().scan(normalized, session_had_injection=bool(metadata.get("session_had_injection")))
    rules = [rule.value for rule in scan.rules_triggered]

    reasons: list[str] = []
    confidence = max(prompt_decision.confidence, scan.confidence)
    if prompt_decision.patterns:
        reasons.append("prompt_guard:" + ",".join(prompt_decision.patterns))
    if rules:
        reasons.extend(rules)

    if PoisonRule.MEM_002_CREDENTIALS in scan.rules_triggered or PoisonRule.MEM_006_ENCODED_PAYLOAD in scan.rules_triggered:
        return IngestVerdict(
            decision="reject",
            confidence=confidence,
            reasons=reasons or ["credential_or_encoded_payload"],
            patterns=list(prompt_decision.patterns),
            trust="rejected",
            preview=_preview(normalized),
        )

    if prompt_decision.blocked or scan.is_poisoned:
        return IngestVerdict(
            decision="quarantine",
            confidence=confidence,
            reasons=reasons or ["injection_or_poison"],
            patterns=list(prompt_decision.patterns),
            trust="quarantined",
            preview=_preview(normalized),
        )

    return IngestVerdict(
        decision="allow",
        confidence=confidence,
        reasons=reasons,
        patterns=list(prompt_decision.patterns),
        trust="trusted",
        preview=_preview(normalized),
    )

