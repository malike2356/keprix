"""Scout protocol types for Keprix security signals and commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SignalSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SignalCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    TOOL_ABUSE = "tool_abuse"
    CREDENTIAL_ACCESS = "credential_access"
    EGRESS_VIOLATION = "egress_violation"
    FILE_VIOLATION = "file_violation"
    A2A_VIOLATION = "a2a_violation"
    RATE_LIMIT = "rate_limit"
    ANOMALY = "anomaly"
    GOVERNANCE = "governance"
    HEARTBEAT = "heartbeat"


class ScoutCommand(str, Enum):
    SUSPEND = "suspend"
    RESUME = "resume"
    BLOCK_SESSION = "block_session"
    UNBLOCK_SESSION = "unblock_session"
    QUARANTINE_TOOL = "quarantine_tool"
    LIFT_QUARANTINE = "lift_quarantine"
    BLOCK_EGRESS = "block_egress"
    UNBLOCK_EGRESS = "unblock_egress"
    SET_RATE_LIMIT = "set_rate_limit"
    CLEAR_RATE_LIMIT = "clear_rate_limit"
    SET_SANDBOX_POLICY = "set_sandbox_policy"
    SET_TOOL_POLICY = "set_tool_policy"
    CLEAR_SESSION_MEMORY = "clear_session_memory"
    ROTATE_CREDENTIALS = "rotate_credentials"
    ACTIVATE_HONEYPOTS = "activate_honeypots"
    SHUTDOWN = "shutdown"
    ROLLBACK_TO_CHECKPOINT = "rollback_to_checkpoint"


@dataclass
class ScoutSignal:
    signal_id: str
    timestamp: str
    agent_id: str
    product: str
    category: SignalCategory
    severity: SignalSeverity
    action: str
    target: str
    details: dict[str, Any] = field(default_factory=dict)
    mitre_tactic: str | None = None
    threat_score: float | None = None
    correlation_id: str | None = None


@dataclass
class ScoutCommandMessage:
    command_id: str
    command: ScoutCommand
    agent_id: str
    session_id: str | None
    params: dict[str, Any]
    issued_by: str
    issued_at: str
    ttl_seconds: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ScoutCommandMessage:
        raw_command = payload.get("command")
        if isinstance(raw_command, ScoutCommand):
            command = raw_command
        else:
            command = ScoutCommand(str(raw_command))
        return cls(
            command_id=str(payload.get("command_id") or ""),
            command=command,
            agent_id=str(payload.get("agent_id") or "*"),
            session_id=payload.get("session_id"),
            params=dict(payload.get("params") or {}),
            issued_by=str(payload.get("issued_by") or "scout"),
            issued_at=str(payload.get("issued_at") or ""),
            ttl_seconds=payload.get("ttl_seconds"),
        )
