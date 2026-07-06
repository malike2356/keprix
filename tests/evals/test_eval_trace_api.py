"""Eval trace API tests (Prompt 200)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.evals.trace_store import get_eval_trace_store, register_adoption_smoke_trace
from keprix.playbook.adoption_release import run_reference_adoption_smoke


@pytest.mark.asyncio
async def test_eval_trace_api_returns_smoke_trace() -> None:
    result = await run_reference_adoption_smoke(workspace_id="trace-smoke-test")
    trace_id = result["trace_id"]
    assert trace_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/evals/traces/{trace_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == trace_id
    assert len(body["spans"]) >= 3
    assert body["linked_run_ids"]["playbook"] == result["playbook_run_id"]


@pytest.mark.asyncio
async def test_eval_suite_task_includes_trace_id() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/evals/run/chat_basics")

    assert response.status_code == 200
    tasks = response.json()["tasks"]
    assert tasks
    assert all(task.get("trace_id") for task in tasks)


@pytest.mark.asyncio
async def test_eval_trace_includes_playbook_link() -> None:
    trace_id = "trace-link-test"
    register_adoption_smoke_trace(
        trace_id=trace_id,
        playbook_run_id="pb-run-123",
        crew_name="crew-a",
        browser_session_id="browser-1",
        analytics_session_id="analytics-1",
        eval_id=trace_id,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/evals/traces/{trace_id}")

    body = response.json()
    assert body["linked_run_ids"]["playbook"] == "pb-run-123"
    assert body["linked_run_ids"]["crew"] == "crew-a"

    store = get_eval_trace_store()
    assert store.get(trace_id) is not None
