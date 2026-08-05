"""Structured agent messages for inter-agent communication (Prompt 58)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from datetime import datetime

from keprix.compat import UTC, StrEnum


class MessageType(StrEnum):
    AGENT = "agent"
    TOOL = "tool"
    APPROVAL = "approval"
    SYSTEM = "system"
    ARTIFACT = "artifact"
    RUN_EVENT = "run_event"


@dataclass(slots=True)
class AgentMessage:
    sender: str
    recipient: str
    workspace_id: str
    run_id: str
    content: str
    message_type: MessageType = MessageType.AGENT
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    artifact_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "workspace_id": self.workspace_id,
            "run_id": self.run_id,
            "content": self.content,
            "message_type": self.message_type.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "artifact_refs": self.artifact_refs,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> AgentMessage:
        return cls(
            sender=str(raw["sender"]),
            recipient=str(raw["recipient"]),
            workspace_id=str(raw["workspace_id"]),
            run_id=str(raw["run_id"]),
            content=str(raw.get("content") or ""),
            message_type=MessageType(str(raw.get("message_type") or MessageType.AGENT)),
            metadata=dict(raw.get("metadata") or {}),
            timestamp=str(raw.get("timestamp") or datetime.now(UTC).isoformat()),
            trace_id=str(raw.get("trace_id") or uuid4()),
            artifact_refs=list(raw.get("artifact_refs") or []),
        )
