"""Trigger builder schemas (schedule + event + actions)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

TriggerKind = Literal["schedule", "event"]
ScheduleType = Literal["interval", "daily", "weekly", "monthly", "cron", "once"]
ActionType = Literal[
    "run_playbook",
    "call_tool",
    "ask_agent",
    "run_mutation",
    "create_task",
    "call_webhook",
    "request_approval",
]
ApprovalMode = Literal["auto", "required", "notify"]
RunStatus = Literal["queued", "running", "awaiting_approval", "done", "failed", "skipped"]

EVENT_SOURCES = frozenset(
    {
        "connector",
        "webhook",
        "run_ledger",
        "repository",
        "workspace",
        "manual",
    }
)

RISKY_ACTIONS = frozenset({"call_tool", "run_mutation", "call_webhook"})


@dataclass
class ScheduleSpec:
    type: ScheduleType
    every_minutes: int | None = None
    at_hour: int | None = None
    at_minute: int | None = None
    weekday: int | None = None  # 0=Sun .. 6=Sat
    day: int | None = None  # 1-31 for monthly
    cron: str | None = None
    at: str | None = None  # ISO for once

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ScheduleSpec | None:
        if not data:
            return None
        return cls(
            type=str(data.get("type") or "interval"),  # type: ignore[arg-type]
            every_minutes=_opt_int(data.get("every_minutes") or data.get("everyMinutes")),
            at_hour=_opt_int(data.get("at_hour") or data.get("atHour")),
            at_minute=_opt_int(data.get("at_minute") if data.get("at_minute") is not None else data.get("atMinute")),
            weekday=_opt_int(data.get("weekday")),
            day=_opt_int(data.get("day")),
            cron=data.get("cron"),
            at=data.get("at"),
        )


@dataclass
class EventSpec:
    source: str  # connector | webhook | run_ledger | repository | workspace | manual
    event_type: str
    filter: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "event_type": self.event_type, "filter": dict(self.filter)}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> EventSpec | None:
        if not data:
            return None
        return cls(
            source=str(data.get("source") or "manual"),
            event_type=str(data.get("event_type") or data.get("eventType") or "*"),
            filter=dict(data.get("filter") or {}),
        )


@dataclass
class ActionSpec:
    type: ActionType
    config: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "config": dict(self.config),
            "requires_approval": self.requires_approval,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ActionSpec:
        if not data or not data.get("type"):
            raise ValueError("action.type is required")
        action_type = str(data["type"])
        if action_type not in {
            "run_playbook",
            "call_tool",
            "ask_agent",
            "run_mutation",
            "create_task",
            "call_webhook",
            "request_approval",
        }:
            raise ValueError(f"Unsupported action type: {action_type}")
        return cls(
            type=action_type,  # type: ignore[arg-type]
            config=dict(data.get("config") or {}),
            requires_approval=bool(data.get("requires_approval") or data.get("requiresApproval")),
        )


@dataclass
class Trigger:
    id: str
    workspace_id: str
    owner_id: str
    name: str
    enabled: bool
    kind: TriggerKind
    schedule: ScheduleSpec | None
    timezone: str
    event: EventSpec | None
    action: ActionSpec
    approval_mode: ApprovalMode
    ai_mode: Literal["managed", "byok"]
    next_run_at: str | None
    last_run_at: str | None
    created_at: str
    updated_at: str
    condition: dict[str, Any] = field(default_factory=dict)
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "owner_id": self.owner_id,
            "name": self.name,
            "enabled": self.enabled,
            "kind": self.kind,
            "schedule": self.schedule.to_dict() if self.schedule else None,
            "timezone": self.timezone,
            "event": self.event.to_dict() if self.event else None,
            "action": self.action.to_dict(),
            "approval_mode": self.approval_mode,
            "ai_mode": self.ai_mode,
            "next_run_at": self.next_run_at,
            "last_run_at": self.last_run_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "condition": dict(self.condition),
            "note": self.note,
        }


@dataclass
class TriggerRun:
    id: str
    trigger_id: str
    workspace_id: str
    owner_id: str
    status: RunStatus
    trigger_kind: str
    payload: dict[str, Any]
    result: dict[str, Any]
    approval_id: str | None
    attempts: int
    locked_at: str | None
    locked_by: str | None
    created_at: str
    finished_at: str | None
    ledger_entry_id: str | None = None
    cost_credits: int | None = None
    quota_impact: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trigger_id": self.trigger_id,
            "workspace_id": self.workspace_id,
            "owner_id": self.owner_id,
            "status": self.status,
            "trigger_kind": self.trigger_kind,
            "payload": dict(self.payload),
            "result": dict(self.result),
            "approval_id": self.approval_id,
            "attempts": self.attempts,
            "locked_at": self.locked_at,
            "locked_by": self.locked_by,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "ledger_entry_id": self.ledger_entry_id,
            "cost_credits": self.cost_credits,
            "quota_impact": self.quota_impact,
        }


def _opt_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def validate_trigger_input(
    *,
    kind: str,
    schedule: dict[str, Any] | None,
    event: dict[str, Any] | None,
    action: dict[str, Any],
) -> tuple[ScheduleSpec | None, EventSpec | None, ActionSpec]:
    if kind not in {"schedule", "event"}:
        raise ValueError("kind must be schedule or event")
    action_spec = ActionSpec.from_dict(action)
    schedule_spec = ScheduleSpec.from_dict(schedule) if kind == "schedule" else None
    event_spec = EventSpec.from_dict(event) if kind == "event" else None
    if kind == "schedule":
        if schedule_spec is None:
            raise ValueError("schedule is required for schedule triggers")
        _validate_schedule(schedule_spec)
    if kind == "event":
        if event_spec is None:
            raise ValueError("event is required for event triggers")
        if event_spec.source not in EVENT_SOURCES:
            raise ValueError(f"Unsupported event source: {event_spec.source}")
    return schedule_spec, event_spec, action_spec


def _validate_schedule(spec: ScheduleSpec) -> None:
    if spec.type == "interval":
        if not spec.every_minutes or spec.every_minutes < 1:
            raise ValueError("interval schedule requires every_minutes >= 1")
    elif spec.type == "daily":
        if spec.at_hour is None:
            raise ValueError("daily schedule requires at_hour")
    elif spec.type == "weekly":
        if spec.weekday is None or spec.at_hour is None:
            raise ValueError("weekly schedule requires weekday and at_hour")
    elif spec.type == "monthly":
        if spec.day is None or spec.at_hour is None:
            raise ValueError("monthly schedule requires day and at_hour")
    elif spec.type == "cron":
        if not (spec.cron or "").strip():
            raise ValueError("cron schedule requires cron expression")
    elif spec.type == "once":
        if not (spec.at or "").strip():
            raise ValueError("once schedule requires at (ISO timestamp)")
    else:
        raise ValueError(f"Unsupported schedule type: {spec.type}")


def action_needs_approval(action: ActionSpec, approval_mode: ApprovalMode) -> bool:
    if approval_mode == "required":
        return True
    if action.requires_approval:
        return True
    if approval_mode == "auto":
        return action.type in RISKY_ACTIONS
    return False
