"""Eval trace registry for drill-down UI (Prompt 200)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EvalTraceRecord:
    trace_id: str
    spans: list[dict[str, Any]] = field(default_factory=list)
    linked_run_ids: dict[str, str] = field(default_factory=dict)
    expected: str | None = None
    actual: str | None = None
    task_id: str | None = None
    suite: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "spans": list(self.spans),
            "linked_run_ids": dict(self.linked_run_ids),
            "expected": self.expected,
            "actual": self.actual,
            "task_id": self.task_id,
            "suite": self.suite,
            "reason": self.reason,
        }


class EvalTraceStore:
    def __init__(self) -> None:
        self._records: dict[str, EvalTraceRecord] = {}

    def register(
        self,
        *,
        trace_id: str | None = None,
        spans: list[dict[str, Any]] | None = None,
        linked_run_ids: dict[str, str] | None = None,
        expected: str | None = None,
        actual: str | None = None,
        task_id: str | None = None,
        suite: str | None = None,
        reason: str | None = None,
    ) -> EvalTraceRecord:
        rid = trace_id or str(uuid.uuid4())
        record = EvalTraceRecord(
            trace_id=rid,
            spans=list(spans or []),
            linked_run_ids=dict(linked_run_ids or {}),
            expected=expected,
            actual=actual,
            task_id=task_id,
            suite=suite,
            reason=reason,
        )
        self._records[rid] = record
        return record

    def append_span(self, trace_id: str, *, name: str, event: str, payload: dict[str, Any] | None = None) -> None:
        record = self._records.get(trace_id)
        if record is None:
            return
        record.spans.append(
            {
                "name": name,
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": payload or {},
            }
        )

    def get(self, trace_id: str) -> EvalTraceRecord | None:
        return self._records.get(trace_id)

    def link_run(self, trace_id: str, key: str, run_id: str) -> None:
        record = self._records.get(trace_id)
        if record is None:
            return
        record.linked_run_ids[key] = run_id


_store: EvalTraceStore | None = None


def get_eval_trace_store() -> EvalTraceStore:
    global _store
    if _store is None:
        _store = EvalTraceStore()
    return _store


def register_playbook_trace(
    *,
    trace_id: str,
    playbook_run_id: str,
    graph_id: str,
    status: str,
    workspace_id: str,
) -> EvalTraceRecord:
    return get_eval_trace_store().register(
        trace_id=trace_id,
        linked_run_ids={"playbook": playbook_run_id},
        spans=[
            {
                "name": "playbook",
                "event": "playbook.completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "graph_id": graph_id,
                    "status": status,
                    "workspace_id": workspace_id,
                    "run_id": playbook_run_id,
                },
            }
        ],
    )


def register_task_trace(
    *,
    task_id: str,
    suite: str,
    expected: str | None,
    actual: str,
    passed: bool,
    reason: str | None,
    category: str,
) -> str:
    trace_id = str(uuid.uuid4())
    get_eval_trace_store().register(
        trace_id=trace_id,
        task_id=task_id,
        suite=suite,
        expected=expected,
        actual=actual,
        reason=reason,
        spans=[
            {
                "name": task_id,
                "event": "eval.scored",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "category": category,
                    "passed": passed,
                    "reason": reason,
                },
            }
        ],
    )
    return trace_id


def register_adoption_smoke_trace(
    *,
    trace_id: str,
    playbook_run_id: str,
    crew_name: str,
    browser_session_id: str | None,
    analytics_session_id: str | None,
    eval_id: str,
) -> EvalTraceRecord:
    linked: dict[str, str] = {
        "playbook": playbook_run_id,
        "crew": crew_name,
        "eval": eval_id,
    }
    if browser_session_id:
        linked["browser"] = browser_session_id
    if analytics_session_id:
        linked["analytics"] = analytics_session_id

    return get_eval_trace_store().register(
        trace_id=trace_id,
        linked_run_ids=linked,
        expected="adoption smoke eval passes",
        actual="Adoption smoke completed with citations.",
        suite="reference-adoption-smoke",
        spans=[
            {
                "name": "playbook",
                "event": "adoption.playbook",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"run_id": playbook_run_id},
            },
            {
                "name": "crew",
                "event": "adoption.crew",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"team": crew_name},
            },
            {
                "name": "browser",
                "event": "adoption.browser",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"session_id": browser_session_id},
            },
            {
                "name": "analytics",
                "event": "adoption.analytics",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"session_id": analytics_session_id},
            },
            {
                "name": "eval",
                "event": "adoption.eval",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"eval_id": eval_id},
            },
        ],
    )
