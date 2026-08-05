"""Runtime data store for live TUI panels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.tui.runtime_events import (
    ApiRuntimeEvent,
    MessageRuntimeMetadata,
    PluginRuntimeItem,
    SkillRuntimeItem,
    SubagentRuntimeEvent,
    ToolRuntimeEvent,
    now_monotonic,
)
from keprix.tui.command_center.runtime_timeline import RuntimeTimeline, RuntimeTimelineEvent


@dataclass
class TurnRuntimeState:
    session_id: str = ""
    model: str = ""
    provider: str = ""
    started_at: float = field(default_factory=now_monotonic)
    finished_at: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float = 0.0
    status: str = "idle"

    @property
    def latency_ms(self) -> int:
        end = self.finished_at or now_monotonic()
        return int(max(0.0, end - self.started_at) * 1000)


class RuntimeStore:
    """Collects live runtime data that powers TUI panels."""

    def __init__(self) -> None:
        self.turn = TurnRuntimeState()
        self.tools: list[ToolRuntimeEvent] = []
        self.subagents: dict[str, SubagentRuntimeEvent] = {}
        self.messages: list[MessageRuntimeMetadata] = []
        self.api_events: list[ApiRuntimeEvent] = []
        self.skills: list[SkillRuntimeItem] = []
        self.plugins: list[PluginRuntimeItem] = []
        self.queue: list[str] = []
        self.timeline = RuntimeTimeline()
        self.files_changed: list[str] = []
        self.commands_executed: list[str] = []
        self.risks_or_warnings: list[str] = []
        self.tests_run: list[str] = []
        self.pending_next_actions: list[str] = []

    def start_turn(self, *, session_id: str, model: str = "", provider: str = "") -> None:
        self.turn = TurnRuntimeState(session_id=session_id, model=model, provider=provider, status="running")
        self.tools.clear()
        self.subagents.clear()
        self.api_events.clear()
        self.timeline = RuntimeTimeline()
        self.files_changed.clear()
        self.commands_executed.clear()
        self.risks_or_warnings.clear()
        self.tests_run.clear()
        self.pending_next_actions.clear()
        self.timeline.add(RuntimeTimelineEvent("turn", "Turn started", session_id, "running"))
        if model:
            self.timeline.add(RuntimeTimelineEvent("model", "Model selected", model))
        if provider:
            self.timeline.add(RuntimeTimelineEvent("model", "Provider selected", provider))

    def finish_turn(self, *, status: str = "complete") -> None:
        self.turn.status = status
        self.turn.finished_at = now_monotonic()
        self.timeline.add(RuntimeTimelineEvent("turn", "Turn finished", status=status))

    def update_usage(self, payload: dict[str, Any]) -> None:
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else payload
        self.turn.input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or self.turn.input_tokens or 0)
        self.turn.output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or self.turn.output_tokens or 0)
        self.turn.total_tokens = int(usage.get("total_tokens") or self.turn.input_tokens + self.turn.output_tokens)
        self.turn.cost_estimate = float(usage.get("cost") or usage.get("cost_estimate") or self.turn.cost_estimate or 0.0)
        self.timeline.add(
            RuntimeTimelineEvent(
                "usage",
                f"{self.turn.total_tokens} tokens",
                f"{self.turn.latency_ms} ms, cost {self.turn.cost_estimate:.4f}",
            )
        )

    def start_tool(self, name: str, *, call_id: str = "", args: dict[str, Any] | None = None) -> ToolRuntimeEvent:
        event = ToolRuntimeEvent(name=name or "tool", call_id=call_id, args=dict(args or {}), status="running")
        self.tools.append(event)
        self.timeline.add(RuntimeTimelineEvent("tool", event.name, call_id, "running"))
        return event

    def finish_tool(
        self,
        name: str,
        *,
        call_id: str = "",
        status: str = "done",
        result_preview: str = "",
        error: str = "",
    ) -> ToolRuntimeEvent:
        event = self._find_tool(name=name, call_id=call_id)
        if event is None:
            event = self.start_tool(name, call_id=call_id)
        event.status = status if status in {"queued", "running", "done", "error", "cancelled"} else "done"  # type: ignore[assignment]
        event.result_preview = result_preview[:500]
        event.error = error[:500]
        event.finished_at = now_monotonic()
        detail = event.error or event.result_preview
        self.timeline.add(RuntimeTimelineEvent("tool", event.name, detail[:120], event.status))
        return event

    def spawn_subagent(self, subagent_id: str, *, label: str = "", parent_id: str = "", preview: str = "") -> SubagentRuntimeEvent:
        sid = subagent_id or f"subagent-{len(self.subagents) + 1}"
        event = SubagentRuntimeEvent(subagent_id=sid, label=label or sid, parent_id=parent_id, preview=preview)
        self.subagents[sid] = event
        self.timeline.add(RuntimeTimelineEvent("subagent", event.label, preview[:120], "running"))
        return event

    def finish_subagent(
        self,
        subagent_id: str,
        *,
        label: str = "",
        status: str = "done",
        preview: str = "",
        cost_hint: str = "",
    ) -> SubagentRuntimeEvent:
        sid = subagent_id or label or f"subagent-{len(self.subagents) + 1}"
        event = self.subagents.get(sid)
        if event is None:
            event = self.spawn_subagent(sid, label=label or sid)
        if label:
            event.label = label
        if preview:
            event.preview = preview
        if cost_hint:
            event.cost_hint = cost_hint
        event.status = status if status in {"queued", "running", "done", "error", "cancelled"} else "done"  # type: ignore[assignment]
        event.finished_at = now_monotonic()
        self.timeline.add(RuntimeTimelineEvent("subagent", event.label, event.preview[:120], event.status))
        return event

    def add_message_metadata(self, metadata: MessageRuntimeMetadata) -> None:
        self.messages.append(metadata)
        self.messages[:] = self.messages[-500:]
        self.timeline.add(RuntimeTimelineEvent("stream", "Message done", metadata.model, metadata.status))

    def add_api_event(self, event: ApiRuntimeEvent) -> None:
        self.api_events.append(event)
        self.api_events[:] = self.api_events[-100:]
        self.timeline.add(RuntimeTimelineEvent("api", f"{event.provider}:{event.model}".strip(":"), f"{event.latency_ms} ms", event.status))

    def set_queue(self, items: list[str]) -> None:
        self.queue = list(items)
        self.timeline.add(RuntimeTimelineEvent("queue", f"{len(self.queue)} queued"))

    def record_review_item(self, kind: str, value: str) -> None:
        cleaned = " ".join(value.split())
        if not cleaned:
            return
        targets = {
            "file_changed": self.files_changed,
            "file": self.files_changed,
            "command_executed": self.commands_executed,
            "command": self.commands_executed,
            "warning": self.risks_or_warnings,
            "risk": self.risks_or_warnings,
            "test_run": self.tests_run,
            "test": self.tests_run,
            "next_action": self.pending_next_actions,
            "todo": self.pending_next_actions,
        }
        bucket = targets.get(kind)
        if bucket is None:
            return
        if cleaned not in bucket:
            bucket.append(cleaned)

    def set_skills(self, skills: list[SkillRuntimeItem]) -> None:
        self.skills = list(skills)

    def set_plugins(self, plugins: list[PluginRuntimeItem]) -> None:
        self.plugins = list(plugins)

    def summary_lines(self) -> list[str]:
        running_tools = sum(1 for item in self.tools if item.status == "running")
        done_tools = sum(1 for item in self.tools if item.status != "running")
        running_subagents = sum(1 for item in self.subagents.values() if item.status == "running")
        done_subagents = len(self.subagents) - running_subagents
        return [
            f"Turn: {self.turn.status}",
            f"Tokens: {self.turn.total_tokens}",
            f"Latency: {self.turn.latency_ms} ms",
            f"Tools: {running_tools} running, {done_tools} done",
            f"Subagents: {running_subagents} running, {done_subagents} done",
            f"API events: {len(self.api_events)}",
        ]

    def _find_tool(self, *, name: str, call_id: str = "") -> ToolRuntimeEvent | None:
        for event in reversed(self.tools):
            if call_id and event.call_id == call_id:
                return event
            if event.name == name and event.status == "running":
                return event
        return None
