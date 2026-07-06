"""Agent app run store tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.agent_apps.run_store import (
    get_last_eval,
    get_run,
    init_run_store,
    list_run_events,
    list_runs,
    prune_old_runs,
    record_lifecycle_event,
    record_run_finish,
    record_run_start,
    save_eval_result,
)


@pytest.fixture()
def isolated_run_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "runs.db"
    monkeypatch.setattr("keprix.agent_apps.run_store._db_path", lambda: db_path)
    init_run_store()
    return db_path


def test_run_store_persists_runs_and_events(isolated_run_db: Path) -> None:
    record_run_start(
        trace_id="trace-1",
        app_name="hello-agent",
        runner="web",
        input_payload={"input": "hello", "context": {"form": {"name": "Ada"}}},
        user_id="alice",
    )
    record_lifecycle_event(
        trace_id="trace-1",
        event="before_run",
        payload={"runner": "web"},
        created_at="2026-01-01T00:00:00+00:00",
    )
    record_run_finish(
        trace_id="trace-1",
        status="success",
        output={"output": "Hello Ada"},
        started_at="2026-01-01T00:00:00+00:00",
    )

    runs = list_runs("hello-agent")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"
    assert runs[0]["input_preview"] == "hello"
    assert runs[0]["duration_ms"] is not None

    detail = get_run("trace-1")
    assert detail is not None
    assert detail["output"]["output"] == "Hello Ada"

    events = list_run_events("trace-1")
    assert len(events) == 1
    assert events[0]["event"] == "before_run"


def test_run_store_prunes_old_runs(isolated_run_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_AGENT_APP_RUN_RETENTION_DAYS", "1")
    record_run_start(
        trace_id="old-run",
        app_name="hello-agent",
        runner="web",
        input_payload={"input": "old"},
    )
    from keprix.agent_apps import run_store as module

    with module._connect() as conn:
        conn.execute(
            "UPDATE runs SET started_at = ? WHERE trace_id = ?",
            ("2020-01-01T00:00:00+00:00", "old-run"),
        )
        conn.commit()
    deleted = prune_old_runs()
    assert deleted >= 1
    assert get_run("old-run") is None


def test_eval_last_result_round_trip(isolated_run_db: Path) -> None:
    payload = {"app": "hello-agent", "passed": 2, "total": 2, "success": True, "cases": []}
    save_eval_result("hello-agent", payload)
    last = get_last_eval("hello-agent")
    assert last is not None
    assert last["result"]["success"] is True
