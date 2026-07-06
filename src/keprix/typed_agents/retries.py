"""Validation retry policy for typed agents."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.typed_agents.schemas import ValidationRepairMessage


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    retry_on_validation: bool = True

    def should_retry(self, attempt: int) -> bool:
        return self.retry_on_validation and attempt < self.max_attempts


@dataclass
class RetryState:
    policy: RetryPolicy = field(default_factory=RetryPolicy)
    attempt: int = 0
    repairs: list[ValidationRepairMessage] = field(default_factory=list)

    def record_repair(self, repair: ValidationRepairMessage) -> ValidationRepairMessage:
        self.attempt += 1
        repair.attempt = self.attempt
        self.repairs.append(repair)
        return repair

    def can_retry(self) -> bool:
        return self.policy.should_retry(self.attempt)
