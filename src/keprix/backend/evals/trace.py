"""Agent run trace model with secret redaction (Prompt 57)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_REDACT_KEYS = frozenset(
    {
        "password",
        "secret",
        "api_key",
        "apikey",
        "token",
        "authorization",
        "bearer",
        "private_key",
        "access_token",
        "refresh_token",
    }
)
_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]\s*\S+", re.IGNORECASE),
]


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return redact_dict(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    return value


def redact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in _REDACT_KEYS:
            out[key] = "[REDACTED]"
        elif isinstance(value, dict):
            out[key] = redact_dict(value)
        elif isinstance(value, list):
            out[key] = [redact_value(item) for item in value]
        elif isinstance(value, str):
            out[key] = redact_value(value)
        else:
            out[key] = value
    return out


@dataclass
class AgentRunTrace:
    run_id: str
    workspace_id: str
    user_request: str
    agent_roles: list[str] = field(default_factory=list)
    playbook_graph: dict[str, Any] = field(default_factory=dict)
    node_transitions: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens: dict[str, int] = field(default_factory=dict)
    cost_estimate_usd: float = 0.0
    artifacts: list[str] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    outcome: str = "pending"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    safety_warnings: list[str] = field(default_factory=list)

    @classmethod
    def start(
        cls,
        *,
        workspace_id: str,
        user_request: str,
        agent_roles: list[str] | None = None,
        playbook_graph: dict[str, Any] | None = None,
    ) -> AgentRunTrace:
        return cls(
            run_id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_request=user_request,
            agent_roles=list(agent_roles or []),
            playbook_graph=dict(playbook_graph or {}),
        )

    def finish(self, outcome: str) -> None:
        self.outcome = outcome
        self.finished_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self, *, redact: bool = True) -> dict[str, Any]:
        payload = {
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "user_request": self.user_request,
            "agent_roles": self.agent_roles,
            "playbook_graph": self.playbook_graph,
            "node_transitions": self.node_transitions,
            "tool_calls": self.tool_calls,
            "model_calls": self.model_calls,
            "tokens": self.tokens,
            "cost_estimate_usd": self.cost_estimate_usd,
            "artifacts": self.artifacts,
            "approvals": self.approvals,
            "errors": self.errors,
            "outcome": self.outcome,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "safety_warnings": self.safety_warnings,
        }
        return redact_dict(payload) if redact else payload
