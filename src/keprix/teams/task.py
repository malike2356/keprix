"""Task model for Keprix crews and flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 1
    retry_on_guardrail_failure: bool = True


@dataclass(slots=True)
class TeamTask:
    id: str
    description: str
    expected_output: str = ""
    role: str = "builder"
    dependencies: list[str] = field(default_factory=list)
    required_artifacts: list[str] = field(default_factory=list)
    output_schema: dict[str, Any] | None = None
    human_review: bool = False
    risk_level: str = "low"
    timeout_seconds: int | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    allow_delegation: bool = False
    output_artifact: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "expected_output": self.expected_output,
            "role": self.role,
            "dependencies": list(self.dependencies),
            "required_artifacts": list(self.required_artifacts),
            "output_schema": self.output_schema,
            "human_review": self.human_review,
            "risk_level": self.risk_level,
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": {
                "max_attempts": self.retry_policy.max_attempts,
                "retry_on_guardrail_failure": self.retry_policy.retry_on_guardrail_failure,
            },
            "allow_delegation": self.allow_delegation,
            "output_artifact": self.output_artifact,
        }


@dataclass(slots=True)
class TaskResult:
    task_id: str
    role: str
    output: Any
    artifact: str | None = None
    attempts: int = 1
    delegated_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "role": self.role,
            "output": self.output,
            "artifact": self.artifact,
            "attempts": self.attempts,
            "delegated_to": self.delegated_to,
        }
