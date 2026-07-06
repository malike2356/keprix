"""Agent app HTTP route tests."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir
from keprix.agent_apps.routes import router as agent_apps_router
from keprix.api.auth import require_api_auth


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    app = FastAPI()
    app.include_router(agent_apps_router)

    async def _fake_auth() -> str:
        return "test-user"

    async def _allow_entitlement(*_args, **_kwargs) -> None:
        return None

    app.dependency_overrides[require_api_auth] = _fake_auth
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_run", _allow_entitlement)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install", _allow_entitlement)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install_catalog_template", _allow_entitlement)
    return TestClient(app)


def test_get_agent_app_detail(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    from keprix.agent_apps.registry import get_agent_app_registry

    get_agent_app_registry().install(sample_app_dir(), source="template", source_id="hello-agent")
    response = client.get("/api/agent-apps/hello-agent")
    assert response.status_code == 200
    payload = response.json()["app"]
    assert payload["name"] == "hello-agent"
    assert payload["display_name"] == "Hello Agent"
    assert "app_dir" not in payload


def test_get_agent_app_not_found(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    response = client.get("/api/agent-apps/does-not-exist")
    assert response.status_code == 404


def test_catalog_list(client: TestClient) -> None:
    response = client.get("/api/agent-apps/catalog")
    assert response.status_code == 200
    templates = response.json()["templates"]
    assert any(item["id"] == "daily-standup" for item in templates)


def test_run_agent_app_with_inputs(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    from keprix.agent_apps.registry import get_agent_app_registry

    get_agent_app_registry().install(sample_app_dir(), source="template", source_id="hello-agent")
    response = client.post(
        "/api/agent-apps/hello-agent/run",
        json={"input": "", "inputs": {"name": "RouteTest"}, "runner": "web"},
    )
    assert response.status_code == 200
    assert "RouteTest" in response.json()["result"]["output"]


def test_agent_app_readiness(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    response = client.post("/api/agent-apps/catalog/daily-standup/install")
    assert response.status_code == 200
    readiness = client.get("/api/agent-apps/daily-standup/readiness")
    assert readiness.status_code == 200
    body = readiness.json()
    assert "missing_env" in body
    assert "missing_permissions" in body
    assert "vault_links" in body


def test_catalog_install(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    response = client.post("/api/agent-apps/catalog/daily-standup/install")
    assert response.status_code == 200
    body = response.json()
    assert body["app"]["name"] == "daily-standup"
    assert body["redirect"] == "/agent-apps/daily-standup"


def test_agent_app_runs_api(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    monkeypatch.setattr("keprix.agent_apps.run_store._db_path", lambda: tmp_path / "runs.db")
    from keprix.agent_apps.registry import get_agent_app_registry
    from keprix.agent_apps.run_store import init_run_store, record_run_finish, record_run_start

    get_agent_app_registry().install(sample_app_dir(), source="template", source_id="hello-agent")
    init_run_store()
    record_run_start(trace_id="t-1", app_name="hello-agent", runner="web", input_payload={"input": "Ada"})
    record_run_finish(trace_id="t-1", status="success", output={"output": "Hello Ada"}, started_at="2026-01-01T00:00:00+00:00")

    listed = client.get("/api/agent-apps/hello-agent/runs")
    assert listed.status_code == 200
    runs = listed.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["input_preview"] == "Ada"

    detail = client.get("/api/agent-apps/runs/t-1")
    assert detail.status_code == 200
    assert detail.json()["run"]["trace_id"] == "t-1"
    assert detail.json()["events"] == []

    events = client.get("/api/agent-apps/runs/t-1/events")
    assert events.status_code == 200
