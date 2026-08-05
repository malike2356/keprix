"""Session replay data assembly for brain graph playback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from keprix.brain.node_resolvers import NodeResolver
from keprix.data_architecture.graph_edges import list_graph_edges_for_session
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _now()


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("content") or "").strip())
        return " ".join(part for part in parts if part).strip()
    return ""


def _message_role(message: dict[str, Any]) -> str:
    role = str(message.get("role") or "user").lower()
    if role in {"assistant", "agent", "aiva"}:
        return "agent"
    return "user"


def _message_timestamp(message: dict[str, Any], *, fallback: datetime) -> datetime:
    for key in ("createdAt", "created_at", "timestamp"):
        if message.get(key):
            return _parse_datetime(message.get(key))
    return fallback


def _relation_label(relation: str, metadata: dict[str, Any]) -> str:
    activation_type = str(metadata.get("activation_type") or "").lower()
    if activation_type in {"memory_retrieved", "document_searched"}:
        return "retrieved"
    if activation_type in {"skill_fired", "skill_selected"}:
        return "skill_fired"
    if activation_type == "tool_called":
        return "tool_called"
    if "retriev" in relation.lower():
        return "retrieved"
    if "skill" in relation.lower():
        return "skill_fired"
    if "tool" in relation.lower() or "called" in relation.lower():
        return "tool_called"
    return relation


@dataclass
class ReplayActivation:
    step: int
    node_kind: str
    node_id: str
    node_label: str
    relation: str
    confidence: float | None
    activated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "node_kind": self.node_kind,
            "node_id": self.node_id,
            "node_label": self.node_label,
            "relation": self.relation,
            "confidence": self.confidence,
            "activated_at": self.activated_at.isoformat(),
        }


@dataclass
class ReplayMessage:
    index: int
    role: str
    content: str
    timestamp: datetime
    activations_before: list[str] = field(default_factory=list)
    activations_during: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "activations_before": self.activations_before,
            "activations_during": self.activations_during,
        }


@dataclass
class SessionReplayData:
    session_id: str
    session_title: str
    session_date: datetime
    messages: list[ReplayMessage]
    activations: list[ReplayActivation]
    activation_count: int = 0
    has_brain_activity: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_title": self.session_title,
            "session_date": self.session_date.isoformat(),
            "messages": [message.to_dict() for message in self.messages],
            "activations": [activation.to_dict() for activation in self.activations],
            "activation_count": self.activation_count,
            "has_brain_activity": self.has_brain_activity,
        }


class SessionReplayService:
    def __init__(self, resolver: NodeResolver | None = None) -> None:
        self.resolver = resolver or NodeResolver()

    async def list_sessions(self, user: dict[str, Any], workspace_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = workspace_repo.list_sessions(user, limit=limit, offset=0)
        sessions: list[dict[str, Any]] = []
        for row in rows:
            session_id = row["id"]
            edges = list_graph_edges_for_session(workspace_id=workspace_id, session_id=session_id)
            activation_count = len(
                [
                    edge
                    for edge in edges
                    if not (edge["source_kind"] == "session" and edge["source_id"] == session_id)
                ]
            )
            created = row.get("created_at")
            sessions.append(
                {
                    "session_id": session_id,
                    "title": row.get("title") or "Conversation",
                    "session_date": created.isoformat() if hasattr(created, "isoformat") else created,
                    "activation_count": activation_count,
                }
            )
        return sessions

    async def build(self, user: dict[str, Any], workspace_id: str, session_id: str) -> SessionReplayData:
        try:
            session = workspace_repo.get_session(user, session_id)
        except NotFoundError as exc:
            raise NotFoundError(session_id) from exc

        raw_messages = session.get("messages") or []
        session_created = _parse_datetime(session.get("created_at"))
        edges = list_graph_edges_for_session(workspace_id=workspace_id, session_id=session_id)

        activations_raw: list[ReplayActivation] = []
        for edge in edges:
            if edge["source_kind"] == "session" and edge["source_id"] == session_id:
                continue
            node_kind = edge["source_kind"]
            node_id = edge["source_id"]
            if edge["target_kind"] != "session" or edge["target_id"] != session_id:
                node_kind = edge["target_kind"]
                node_id = edge["target_id"]
            if node_kind == "session":
                continue
            metadata = dict(edge.get("metadata") or {})
            confidence = metadata.get("confidence")
            resolved = await self.resolver.resolve(workspace_id, node_kind, node_id)
            label = resolved.label if resolved else node_id
            activations_raw.append(
                ReplayActivation(
                    step=0,
                    node_kind=node_kind,
                    node_id=node_id,
                    node_label=label,
                    relation=_relation_label(edge["relation"], metadata),
                    confidence=float(confidence) if confidence is not None else None,
                    activated_at=_parse_datetime(edge.get("created_at")),
                )
            )

        activations_raw.sort(key=lambda item: item.activated_at)
        activation_count = len(activations_raw)

        messages: list[ReplayMessage] = []
        previous_ts = session_created
        for index, raw in enumerate(raw_messages):
            timestamp = _message_timestamp(raw, fallback=previous_ts)
            previous_ts = timestamp
            messages.append(
                ReplayMessage(
                    index=index,
                    role=_message_role(raw),
                    content=_message_text(raw),
                    timestamp=timestamp,
                )
            )

        if not messages:
            messages.append(
                ReplayMessage(
                    index=0,
                    role="agent",
                    content="No transcript recorded for this session.",
                    timestamp=session_created,
                )
            )

        message_times = [message.timestamp for message in messages]

        def node_key(kind: str, node_id: str) -> str:
            return f"{kind}:{node_id}"

        for activation in activations_raw:
            step = len(messages) - 1
            for index, timestamp in enumerate(message_times):
                if activation.activated_at <= timestamp:
                    step = index
                    break
            activation.step = step

        for index, message in enumerate(messages):
            step_activations = [
                activation
                for activation in activations_raw
                if activation.step == index and activation.node_kind != "session"
            ]
            keys = [node_key(activation.node_kind, activation.node_id) for activation in step_activations]
            if message.role == "user":
                message.activations_before = keys
            else:
                message.activations_during = keys

        return SessionReplayData(
            session_id=session_id,
            session_title=str(session.get("title") or "Conversation"),
            session_date=session_created,
            messages=messages,
            activations=activations_raw,
            activation_count=activation_count,
            has_brain_activity=activation_count > 0,
        )
