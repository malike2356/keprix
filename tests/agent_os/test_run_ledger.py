"""Prompt 261 run ledger tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from keprix.agent_os.hooks import record_external_run
from keprix.agent_os.run_ledger_store import RunLedgerStore
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.playbook.sdk_workflow import start_workflow_run
from keprix.workspace.template_presets import create_workspace, workspace_root


def test_external_run_records_and_exports_to_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    create_workspace("client one", "blank")

    entry = record_external_run(
        source_type="skill",
        source_id="brief",
        run_id="run-1",
        workspace_id="client one",
        status="completed",
        input_summary={"topic": "market"},
        output_summary={"summary": "done"},
        eval_score=0.92,
        tokens=125,
        duration_ms=41,
    )

    loaded = RunLedgerStore().get(entry.entry_id)
    assert loaded is not None
    assert loaded.tokens == 125
    export_path = workspace_root("client one") / "runs" / f"{entry.entry_id}.json"
    assert export_path.exists()


def test_playbook_completion_creates_ledger_entry_with_runtime_metrics(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))

    run = asyncio.run(
        start_workflow_run(
            {
                "graph_id": "ledger_playbook",
                "steps": [
                    {
                        "id": "done",
                        "type": "task",
                        "config": {"set": {"_eval_score": 0.88, "_token_usage": {"total_tokens": 77}}},
                    }
                ],
            },
            workspace_id="default",
            initial_state={"objective": "ship"},
        )
    )

    entry = RunLedgerStore().get_by_run(run.run_id)
    assert entry is not None
    assert entry.source_type == "playbook"
    assert entry.source_id == "ledger_playbook"
    assert entry.status == "completed"
    assert entry.tokens == 77
    assert entry.eval_score == 0.88
    assert entry.duration_ms >= 0


def test_ledger_routes_list_detail_and_auth(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    entry = record_external_run(
        source_type="agent_app",
        source_id="triage",
        run_id="app-run",
        workspace_id="default",
        status="completed",
    )
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    response = client.get("/api/agent-os/ledger?source_type=agent_app&source_id=triage")
    assert response.status_code == 200
    assert response.json()["entries"][0]["entry_id"] == entry.entry_id
    detail = client.get(f"/api/agent-os/ledger/{entry.entry_id}")
    assert detail.status_code == 200
    assert detail.json()["run_id"] == "app-run"


def test_ledger_routes_respect_agent_os_feature_flag(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "0")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    assert client.get("/api/agent-os/ledger").status_code == 403
