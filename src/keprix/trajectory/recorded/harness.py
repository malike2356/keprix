"""Offline replay harness for recorded trajectory fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix.trajectory.recorded.fixture import (
    RecordedFixture,
    fixture_from_events,
    load_fixture,
    write_fixture,
)
from keprix.trajectory.service import TrajectoryService
from keprix.trajectory.store import TrajectoryStore


@dataclass
class ReplayReport:
    """Outcome of an offline recorded fixture run."""

    fixture_id: str
    trajectory_id: str
    step_count: int
    tool_names_in_order: list[str]
    soft_wall_outcomes: list[str]
    mutation_stages: list[str]
    final_event_type: str | None
    replay: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)


def import_fixture(
    fixture: RecordedFixture,
    *,
    store: TrajectoryStore | None = None,
    service: TrajectoryService | None = None,
) -> tuple[TrajectoryService, str]:
    """Load fixture events into an ephemeral trajectory; return (svc, tid)."""
    if service is None:
        if store is None:
            raise ValueError("pass store= or service=")
        service = TrajectoryService(store=store)
    traj = service.create(
        workspace_id=fixture.workspace_id,
        title=fixture.title or fixture.fixture_id,
        metadata={
            "fixture_id": fixture.fixture_id,
            "recorded_session": True,
        },
    )
    tid = traj["trajectory_id"]
    for event in sorted(fixture.events, key=lambda e: int(e["seq"])):
        service.append(
            tid,
            event["event_type"],
            event.get("payload") or {},
            tool_name=event.get("tool_name"),
            soft_wall_outcome=event.get("soft_wall_outcome"),
            error_text=event.get("error_text"),
            timestamp=event.get("timestamp"),
        )
    return service, tid


def _tool_names_in_order(events: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for event in events:
        if event.get("event_type") != "tool_call":
            continue
        name = event.get("tool_name") or (event.get("payload") or {}).get("name")
        if name:
            out.append(str(name))
    return out


def _soft_wall_outcomes(events: list[dict[str, Any]]) -> list[str]:
    return [
        str(e["soft_wall_outcome"])
        for e in events
        if e.get("event_type") == "soft_wall" and e.get("soft_wall_outcome")
    ]


def _mutation_stages(events: list[dict[str, Any]]) -> list[str]:
    stages: list[str] = []
    for event in events:
        if event.get("event_type") != "mutation":
            continue
        stage = (event.get("payload") or {}).get("stage")
        if stage:
            stages.append(str(stage))
    return stages


def assert_fixture_expectations(
    fixture: RecordedFixture,
    report: ReplayReport,
) -> None:
    """Structural asserts (prefer tools/statuses over exact LLM prose)."""
    exp = fixture.expectations or {}
    if exp.get("require_recorded_replay", True):
        assert report.replay.get("mode") == "recorded"
        assert all(step.get("execute") is False for step in report.replay.get("steps") or [])
        assert all(
            step.get("use_recorded_result") for step in report.replay.get("steps") or []
        )
    if exp.get("forbid_live_execute", True):
        assert all(step.get("execute") is False for step in report.replay.get("steps") or [])

    if "tool_names_in_order" in exp:
        assert report.tool_names_in_order == list(exp["tool_names_in_order"]), (
            f"tool order {report.tool_names_in_order!r} != {exp['tool_names_in_order']!r}"
        )
    if "soft_wall_outcomes" in exp:
        assert report.soft_wall_outcomes == list(exp["soft_wall_outcomes"]), (
            f"soft_wall {report.soft_wall_outcomes!r} != {exp['soft_wall_outcomes']!r}"
        )
    if "mutation_stages" in exp:
        assert report.mutation_stages == list(exp["mutation_stages"]), (
            f"mutation stages {report.mutation_stages!r} != {exp['mutation_stages']!r}"
        )
    if "final_event_type" in exp:
        assert report.final_event_type == exp["final_event_type"]
    if "min_event_count" in exp:
        assert report.step_count >= int(exp["min_event_count"])
    if "final_message_shape" in exp:
        shape = exp["final_message_shape"]
        messages = [e for e in report.events if e.get("event_type") == "message"]
        assert messages, "expected at least one message event"
        last = messages[-1]
        payload = last.get("payload") or {}
        for key, value in shape.items():
            assert payload.get(key) == value, f"message.{key}={payload.get(key)!r} != {value!r}"


def run_recorded_fixture(
    path: Path | str | RecordedFixture,
    *,
    store: TrajectoryStore | None = None,
    sqlite_path: Path | None = None,
) -> ReplayReport:
    """Import fixture, replay recorded-only, assert expectations, return report.

    Never opens a network LLM provider. Callers must not set live mode.
    """
    fixture = path if isinstance(path, RecordedFixture) else load_fixture(path)
    if store is None:
        if sqlite_path is None:
            raise ValueError("pass store= or sqlite_path=")
        store = TrajectoryStore(sqlite_path=sqlite_path)
    service, tid = import_fixture(fixture, store=store)
    replay = service.replay(tid, mode="recorded")
    events = [e.to_dict() for e in service.store.list_events(tid)]
    report = ReplayReport(
        fixture_id=fixture.fixture_id,
        trajectory_id=tid,
        step_count=int(replay.get("step_count") or 0),
        tool_names_in_order=_tool_names_in_order(events),
        soft_wall_outcomes=_soft_wall_outcomes(events),
        mutation_stages=_mutation_stages(events),
        final_event_type=events[-1]["event_type"] if events else None,
        replay=replay,
        events=events,
    )
    assert_fixture_expectations(fixture, report)
    return report


def export_recorded_fixture(
    service: TrajectoryService,
    trajectory_id: str,
    *,
    fixture_id: str,
    path: Path | str,
    expectations: dict[str, Any] | None = None,
    title: str = "",
    description: str = "",
) -> Path:
    """Export a live trajectory to a scrubbed fixture file (local / owner only)."""
    exported = service.store.export_events_for_fixture(trajectory_id)
    fixture = fixture_from_events(
        fixture_id=fixture_id,
        events=exported,
        expectations=expectations,
        title=title,
        description=description,
        workspace_id="fixture",
    )
    return write_fixture(path, fixture)
