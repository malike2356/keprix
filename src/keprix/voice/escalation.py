"""Escalation policy for phone voice calls."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.voice.personas.receptionist import should_escalate


@dataclass
class EscalationPolicy:
    transfer_to: str | None = None
    trigger_keywords: list[str] = field(default_factory=lambda: ["human", "manager", "complaint", "refund"])
    max_duration_seconds: int = 15 * 60


class EscalationEngine:
    def __init__(self, policy: EscalationPolicy | None = None) -> None:
        self.policy = policy or EscalationPolicy()

    def should_escalate(self, transcript: str, *, duration_seconds: int = 0, tool_failed: bool = False) -> bool:
        lowered = transcript.lower()
        return (
            should_escalate(transcript)
            or any(keyword in lowered for keyword in self.policy.trigger_keywords)
            or duration_seconds >= self.policy.max_duration_seconds
            or tool_failed
        )

    def handoff_message(self) -> str:
        return "Let me connect you with someone who can help now."
