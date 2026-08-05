"""Canonical Channel Shield types shared by all adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


CHANNELS = (
    "email",
    "slack",
    "teams",
    "telegram",
    "whatsapp",
    "discord",
    "sms",
    "web",
)


class Channel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    SMS = "sms"
    WEB = "web"


class Verdict(str, Enum):
    CLEAN = "clean"
    SUSPECT = "suspect"
    MALICIOUS = "malicious"
    ERROR = "error"


class PolicyLabel(str, Enum):
    CLEAN = "clean"
    SAFE_SUMMARY_ONLY = "safe_summary_only"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    BLOCKED = "blocked"
    DESTROYED = "destroyed"


class MessageStatus(str, Enum):
    PENDING = "pending"
    ANALYSING = "analysing"
    DELIVERED = "delivered"
    QUARANTINED = "quarantined"
    RELEASED = "released"
    DESTROYED = "destroyed"


@dataclass
class ShieldAttachment:
    id: str
    filename: str
    content_type: str
    size: int
    sha256: str
    storage_uri: str
    extension: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "sha256": self.sha256,
            "storage_uri": self.storage_uri,
            "extension": self.extension,
            "metadata": self.metadata,
        }


@dataclass
class ShieldEnvelope:
    """Channel-agnostic inbound message for the shared pipeline."""

    channel: str
    protection_id: str
    external_message_id: str
    conversation_id: str
    from_addr: str
    to_addrs: list[str]
    text: str
    links: list[str] = field(default_factory=list)
    attachments: list[ShieldAttachment] = field(default_factory=list)
    raw_storage_uri: str = ""
    auth_signals: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    subject: str = ""
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "protectionId": self.protection_id,
            "externalMessageId": self.external_message_id,
            "conversationId": self.conversation_id,
            "from": self.from_addr,
            "to": list(self.to_addrs),
            "text": self.text,
            "links": list(self.links),
            "attachments": [a.to_dict() for a in self.attachments],
            "rawStorageUri": self.raw_storage_uri,
            "authSignals": dict(self.auth_signals),
            "metadata": dict(self.metadata),
            "subject": self.subject,
            "receivedAt": self.received_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShieldEnvelope:
        attachments = []
        for item in data.get("attachments") or []:
            attachments.append(
                ShieldAttachment(
                    id=str(item.get("id") or ""),
                    filename=str(item.get("filename") or "attachment"),
                    content_type=str(item.get("content_type") or item.get("contentType") or "application/octet-stream"),
                    size=int(item.get("size") or 0),
                    sha256=str(item.get("sha256") or ""),
                    storage_uri=str(item.get("storage_uri") or item.get("storageUri") or ""),
                    extension=str(item.get("extension") or ""),
                    metadata=dict(item.get("metadata") or {}),
                )
            )
        received = data.get("received_at") or data.get("receivedAt")
        if isinstance(received, str):
            received_at = datetime.fromisoformat(received.replace("Z", "+00:00"))
        elif isinstance(received, datetime):
            received_at = received
        else:
            received_at = datetime.now(timezone.utc)
        return cls(
            channel=str(data.get("channel") or ""),
            protection_id=str(data.get("protection_id") or data.get("protectionId") or ""),
            external_message_id=str(
                data.get("external_message_id") or data.get("externalMessageId") or ""
            ),
            conversation_id=str(data.get("conversation_id") or data.get("conversationId") or ""),
            from_addr=str(data.get("from") or data.get("from_addr") or ""),
            to_addrs=list(data.get("to") or data.get("to_addrs") or []),
            text=str(data.get("text") or ""),
            links=list(data.get("links") or []),
            attachments=attachments,
            raw_storage_uri=str(data.get("raw_storage_uri") or data.get("rawStorageUri") or ""),
            auth_signals=dict(data.get("auth_signals") or data.get("authSignals") or {}),
            metadata=dict(data.get("metadata") or {}),
            subject=str(data.get("subject") or ""),
            received_at=received_at,
        )


@dataclass
class StageResult:
    stage: str
    ok: bool
    findings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "ok": self.ok,
            "findings": list(self.findings),
            "details": dict(self.details),
        }


@dataclass
class AgentSafeContent:
    """Content safe for assistants, employee agents, skills, playbooks, and UI."""

    policy_label: PolicyLabel
    text: str
    subject: str
    domains: list[str] = field(default_factory=list)
    domain_labels: list[str] = field(default_factory=list)
    attachment_metadata: list[dict[str, Any]] = field(default_factory=list)
    verdict: str = ""
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    redaction_reasons: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_evidence_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "policyLabel": self.policy_label.value,
            "text": self.text,
            "subject": self.subject,
            "domains": list(self.domains),
            "domainLabels": list(self.domain_labels),
            "attachmentMetadata": list(self.attachment_metadata),
            "verdict": self.verdict,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "redactionReasons": list(self.redaction_reasons),
            "allowedActions": list(self.allowed_actions),
            "provenance": dict(self.provenance),
            "rawEvidenceRef": self.raw_evidence_ref,
        }


@dataclass
class PipelineReport:
    verdict: Verdict
    stages: list[StageResult] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    threat_score: float = 0.0
    scout_signal_ids: list[str] = field(default_factory=list)
    raw_evidence_ref: str = ""
    agent_safe_content: dict[str, Any] = field(default_factory=dict)
    policy_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "stages": [s.to_dict() for s in self.stages],
            "reasons": list(self.reasons),
            "threatScore": self.threat_score,
            "scoutSignalIds": list(self.scout_signal_ids),
            "rawEvidenceRef": self.raw_evidence_ref,
            "agentSafeContent": dict(self.agent_safe_content),
            "policyLabel": self.policy_label,
        }
