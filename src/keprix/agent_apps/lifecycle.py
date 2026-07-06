"""Agent lifecycle hooks and trace emission."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from keprix.agent_apps.run_store import list_run_events, list_runs, record_lifecycle_event


class LifecycleEvent(str, Enum):
    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_ERROR = "on_error"
    ON_APPROVAL_REQUESTED = "on_approval_requested"
    ON_ARTIFACT_CREATED = "on_artifact_created"


LifecycleHook = Callable[["LifecycleTrace"], None]


@dataclass
class LifecycleTrace:
    trace_id: str
    app_name: str
    event: LifecycleEvent
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event"] = self.event.value
        return data


class LifecycleBus:
    def __init__(self, *, app_name: str, trace_id: str | None = None) -> None:
        self.app_name = app_name
        self.trace_id = trace_id or str(uuid.uuid4())
        self._hooks: dict[LifecycleEvent, list[LifecycleHook]] = {event: [] for event in LifecycleEvent}
        self.traces: list[LifecycleTrace] = []

    def on(self, event: LifecycleEvent, hook: LifecycleHook) -> None:
        self._hooks[event].append(hook)

    def emit(self, event: LifecycleEvent, payload: dict[str, Any] | None = None) -> LifecycleTrace:
        trace = LifecycleTrace(
            trace_id=self.trace_id,
            app_name=self.app_name,
            event=event,
            payload=payload or {},
        )
        self.traces.append(trace)
        for hook in self._hooks[event]:
            hook(trace)
        try:
            record_lifecycle_event(
                trace_id=trace.trace_id,
                event=trace.event.value,
                payload=trace.payload,
                created_at=trace.created_at,
            )
        except Exception:
            pass
        return trace


_global_traces: dict[str, list[dict[str, Any]]] = {}


def store_run_traces(app_name: str, traces: list[LifecycleTrace], *, trace_id: str | None = None) -> None:
    serialized = [trace.to_dict() for trace in traces]
    key = trace_id or (traces[0].trace_id if traces else app_name)
    _global_traces[key] = serialized
    _global_traces[app_name] = serialized


def get_run_traces(app_name: str, trace_id: str | None = None) -> list[dict[str, Any]]:
    if trace_id:
        events = list_run_events(trace_id)
        if events:
            return [
                {
                    "trace_id": trace_id,
                    "app_name": app_name,
                    "event": item["event"],
                    "payload": item["payload"],
                    "created_at": item["created_at"],
                }
                for item in events
            ]
    latest = list_runs(app_name, limit=1)
    if latest:
        return list_run_events(latest[0]["trace_id"])
    return list(_global_traces.get(app_name, []))
