from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionStep:
    entity: str
    operation: str
    fields: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    confirmation_required: bool = False
    confidence: float = 0.0
    result: Any = None


@dataclass
class ActionPlan:
    user_input: str
    session_id: str | None
    steps: list[ActionStep]
    requires_confirmation: bool = False
    confirmation_prompt: str = ""
    plan_id: str | None = None


@dataclass
class ExecutionResult:
    success: bool
    steps: list[ActionStep]
