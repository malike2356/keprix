"""Contract tests for the TypeScript SDK (Prompt 70)."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.server import create_app
from keprix.public_api.keys import ApiKeyStore, CreateApiKeyRequest
from keprix.sdk.routes import TYPESCRIPT_SDK_MANIFEST

ROOT = Path(__file__).resolve().parents[2]
SDK_ROOT = ROOT / "sdk" / "typescript"
SDK_SRC = SDK_ROOT / "src"


@pytest.fixture(autouse=True)
def disable_database(monkeypatch):
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.public_api.auth.effective_access_level", lambda: "developer")


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


def test_typescript_sdk_files_exist():
    required = [
        "src/agent.ts",
        "src/workflow.ts",
        "src/memory.ts",
        "src/rag.ts",
        "src/evals.ts",
        "src/tools.ts",
        "src/local-dev.ts",
        "src/index.ts",
        "examples/basic-agent.ts",
        "examples/workflow.ts",
        "examples/rag-agent.ts",
        "README.md",
        "package.json",
    ]
    for rel in required:
        assert (SDK_ROOT / rel).is_file(), f"missing sdk/typescript/{rel}"


def test_typescript_modules_reference_backend_endpoints():
    workflow = (SDK_SRC / "workflow.ts").read_text(encoding="utf-8")
    memory = (SDK_SRC / "memory.ts").read_text(encoding="utf-8")
    evals = (SDK_SRC / "evals.ts").read_text(encoding="utf-8")
    agent = (SDK_SRC / "agent.ts").read_text(encoding="utf-8")

    assert "/api/playbook-runs/start" in workflow
    assert "/api/memory/save" in memory
    assert "/api/sdk/typescript/evals/run" in evals
    assert "/v1/chat/completions" in agent


@pytest.mark.asyncio
async def test_typescript_manifest_endpoint(client):
    response = await client.get("/api/sdk/typescript/manifest")
    assert response.status_code == 200
    payload = response.json()
    assert payload["package"] == TYPESCRIPT_SDK_MANIFEST["package"]
    assert "workflow" in payload["modules"]
    assert payload["endpoints"]["workflow_start"] == "/api/playbook-runs/start"


@pytest.mark.asyncio
async def test_typescript_eval_runner_trace_format(client):
    response = await client.post(
        "/api/sdk/typescript/evals/run",
        json={
            "suite_name": "contract-suite",
            "cases": [
                {"name": "echo", "input": "ping", "expect_equals": "ping"},
                {"name": "fail", "input": "no", "expect_equals": "yes"},
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["passed"] == 1
    assert payload["traces"]
    first = payload["traces"][0]
    assert first["event"] == "before_run"
    assert "trace_id" in first
    assert "created_at" in first


@pytest.mark.asyncio
async def test_workflow_start_maps_to_playbook_run(client):
    response = await client.post(
        "/api/playbook-runs/start",
        json={
            "workspace_id": "sdk-test",
            "graph_id": "contract-workflow",
            "steps": [
                {"id": "one", "type": "task", "config": {"key": "done", "value": True}},
                {"id": "two", "type": "artifact", "config": {"name": "out", "content": "ok"}},
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_id"] == "contract-workflow"
    assert payload["status"] == "completed"
    assert payload["state"]["done"] is True
    assert payload["artifacts"]


@pytest.mark.asyncio
async def test_workflow_approval_resume(client):
    start = await client.post(
        "/api/playbook-runs/start",
        json={
            "graph_id": "approval-flow",
            "steps": [
                {"id": "gate", "type": "approval", "config": {"message": "approve?"}},
                {"id": "finish", "type": "task", "config": {"key": "ok", "value": 1}},
            ],
        },
    )
    run_id = start.json()["run_id"]
    assert start.json()["status"] == "waiting_for_approval"

    resumed = await client.post(
        f"/api/playbook-runs/{run_id}/resume",
        json={"state_patch": {"gate_approved": True}, "approved_by": "tester"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_sdk_app_foundation_still_available(client, tmp_path, monkeypatch):
    store = ApiKeyStore(path=tmp_path / "api_keys.json")
    monkeypatch.setattr("keprix.public_api.keys.get_api_key_store", lambda: store)
    monkeypatch.setattr("keprix.public_api.auth.get_api_key_store", lambda: store)
    created = store.create(CreateApiKeyRequest(name="sdk"))
    response = await client.get(
        "/api/sdk/typescript/manifest",
        headers={"Authorization": f"Bearer {created.secret}"},
    )
    assert response.status_code == 200
