"""Playbook run HTTP API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.playbook.runtime import (
    END,
    PlaybookGraph,
    PlaybookRunner,
    RunStatus,
    playbook_registry,
)


@pytest.mark.asyncio
async def test_list_playbook_runs_and_graphs():
    graph = PlaybookGraph("list-test")
    graph.add_node("done", lambda state: {**state, "ok": True})
    graph.add_edge("done", END)
    runner = PlaybookRunner(graph.compile())
    run = await runner.start(workspace_id="default")
    playbook_registry.register(run, runner)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_resp = await client.get("/api/playbook-runs?workspace_id=default")
        assert list_resp.status_code == 200
        payload = list_resp.json()
        assert payload["count"] >= 1
        assert any(item["run_id"] == run.run_id for item in payload["runs"])

        graphs_resp = await client.get("/api/playbook-runs/graphs")
        assert graphs_resp.status_code == 200
        graphs = graphs_resp.json()["graphs"]
        assert any(item["graph_id"] == "sdk-workflow" for item in graphs)


@pytest.mark.asyncio
async def test_start_playbook_from_template_catalog():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/playbook-runs/start",
            json={"graph_id": "sdk-workflow", "workspace_id": "default"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["graph_id"] == "sdk-workflow"
    assert body["status"] in {
        RunStatus.RUNNING.value,
        RunStatus.WAITING_FOR_APPROVAL.value,
        RunStatus.COMPLETED.value,
        RunStatus.INTERRUPTED.value,
    }


@pytest.mark.asyncio
async def test_get_playbook_run_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/playbook-runs/missing-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_playbook_run_api_lifecycle():
    graph = PlaybookGraph("api-test")

    def gate(state):
        from keprix.playbook.runtime import interrupt

        if not state.get("approved"):
            interrupt("needs approval", approval_request={"risk": "publish"})
        return {**state, "published": True}

    graph.add_node("gate", gate)
    graph.add_edge("gate", END)

    runner = PlaybookRunner(graph.compile())
    run = await runner.start(workspace_id="ws-api")
    playbook_registry.register(run, runner)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        get_resp = await client.get(f"/api/playbook-runs/{run.run_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == RunStatus.WAITING_FOR_APPROVAL.value

        events_resp = await client.get(f"/api/playbook-runs/{run.run_id}/events")
        assert events_resp.status_code == 200
        events = events_resp.json()["events"]
        assert any(e["event_type"] == "playbook.approval.requested" for e in events)

        resume_resp = await client.post(
            f"/api/playbook-runs/{run.run_id}/resume",
            json={"state_patch": {"approved": True}, "approved_by": "test-user"},
        )
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == RunStatus.COMPLETED.value

        cancel_resp = await client.post(f"/api/playbook-runs/{run.run_id}/cancel")
        assert cancel_resp.status_code == 400
