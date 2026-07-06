"""Agent app schedule and webhook tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.agent_apps import automation as automation_module
from keprix.agent_apps.public_routes import router as agent_apps_public_router
from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir
from keprix.agent_apps.routes import router as agent_apps_router
from keprix.api.auth import require_api_auth


class _FakeCronJobs:
    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, Any]] = {}

    def create_job(self, **kwargs: Any) -> dict[str, Any]:
        job_id = f"job{len(self.jobs) + 1}"
        job = {
            "id": job_id,
            "name": kwargs.get("name") or job_id,
            "prompt": kwargs.get("prompt") or "",
            "schedule": kwargs.get("schedule"),
            "enabled": True,
            "state": "scheduled",
        }
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self.jobs.get(job_id)

    def update_job(self, job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        job.update(updates)
        return job

    def pause_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        job["enabled"] = False
        job["state"] = "paused"
        return job

    def resume_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        job["enabled"] = True
        job["state"] = "scheduled"
        return job

    def remove_job(self, job_id: str) -> bool:
        return self.jobs.pop(job_id, None) is not None


@pytest.fixture()
def automation_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[AgentAppRegistry, _FakeCronJobs]:
    from keprix.agent_apps import registry as registry_module

    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    monkeypatch.setattr(registry_module, "_registry", registry)
    monkeypatch.setattr(automation_module, "_automation_root", lambda: tmp_path / "registry")
    fake_cron = _FakeCronJobs()
    monkeypatch.setattr(automation_module, "_cron_jobs_module", lambda: fake_cron)
    registry.install(sample_app_dir(), source="template", source_id="hello-agent")
    return registry, fake_cron


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    monkeypatch.setattr(automation_module, "_automation_root", lambda: tmp_path / "registry")
    fake_cron = _FakeCronJobs()
    monkeypatch.setattr(automation_module, "_cron_jobs_module", lambda: fake_cron)

    app = FastAPI()
    app.include_router(agent_apps_router)
    app.include_router(agent_apps_public_router)

    async def _fake_auth() -> str:
        return "test-user"

    async def _allow(*_args, **_kwargs) -> None:
        return None

    async def _noop_audit(*_args, **_kwargs) -> None:
        return None

    app.dependency_overrides[require_api_auth] = _fake_auth
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_run", _allow)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install", _allow)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install_catalog_template", _allow)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_schedule", _allow)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_webhook", _allow)
    monkeypatch.setattr("keprix.agent_apps.routes.audit_log", _noop_audit)
    return TestClient(app)


def test_schedule_crud(automation_env: tuple[AgentAppRegistry, _FakeCronJobs]) -> None:
    schedule = automation_module.upsert_schedule(
        "hello-agent",
        cron="0 9 * * 1-5",
        timezone_name="Europe/London",
        inputs={"focus": "Weekly goals"},
        enabled=True,
    )
    assert schedule["cron"] == "0 9 * * 1-5"
    assert schedule["cron_job_id"]
    loaded = automation_module.get_schedule("hello-agent")
    assert loaded is not None
    assert loaded["enabled"] is True

    automation_module.upsert_schedule(
        "hello-agent",
        cron="0 10 * * *",
        timezone_name="UTC",
        inputs={},
        enabled=False,
    )
    paused = automation_module.get_schedule("hello-agent")
    assert paused is not None
    assert paused["cron"] == "0 10 * * *"
    assert paused["enabled"] is False

    assert automation_module.delete_schedule("hello-agent")
    assert automation_module.get_schedule("hello-agent") is None


def test_uninstall_clears_automation(automation_env: tuple[AgentAppRegistry, _FakeCronJobs]) -> None:
    registry, _fake_cron = automation_env
    automation_module.upsert_schedule(
        "hello-agent",
        cron="0 9 * * *",
        timezone_name="UTC",
        inputs={},
        enabled=True,
    )
    automation_module.rotate_webhook("hello-agent")
    registry.uninstall("hello-agent")
    assert automation_module.get_schedule("hello-agent") is None
    assert automation_module.get_webhook("hello-agent") is None


def test_schedule_routes(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module
    from keprix.agent_apps.registry import get_agent_app_registry

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    get_agent_app_registry().install(sample_app_dir(), source="template", source_id="hello-agent")

    create = client.post(
        "/api/agent-apps/hello-agent/schedule",
        json={"cron": "0 9 * * *", "timezone": "UTC", "inputs": {}, "enabled": True},
    )
    assert create.status_code == 200
    assert create.json()["schedule"]["cron_job_id"]

    get_resp = client.get("/api/agent-apps/hello-agent/schedule")
    assert get_resp.status_code == 200
    assert get_resp.json()["schedule"]["cron"] == "0 9 * * *"

    delete = client.delete("/api/agent-apps/hello-agent/schedule")
    assert delete.status_code == 200
    assert client.get("/api/agent-apps/hello-agent/schedule").json()["schedule"] is None


def test_webhook_bad_token(client: TestClient) -> None:
    response = client.post("/api/public/agent-apps/hooks/invalid-token", json={"inputs": {}})
    assert response.status_code == 401


def test_webhook_good_token(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module
    from keprix.agent_apps.registry import get_agent_app_registry

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    get_agent_app_registry().install(sample_app_dir(), source="template", source_id="hello-agent")
    rotated = automation_module.rotate_webhook("hello-agent")
    token = rotated["url"].rsplit("/", 1)[-1]

    mock_result = {
        "app": "hello-agent",
        "runner": "api",
        "result": {"output": "Webhook ok", "status": "ok"},
    }
    monkeypatch.setattr(automation_module, "execute_agent_app_job", lambda _payload: mock_result)

    response = client.post(f"/api/public/agent-apps/hooks/{token}", json={"inputs": {"name": "Hook"}})
    assert response.status_code == 200
    assert response.json()["result"]["output"] == "Webhook ok"


def test_cron_job_source(automation_env: tuple[AgentAppRegistry, _FakeCronJobs]) -> None:
    source = automation_module.cron_job_source(
        {
            "job_type": "agent_app_run",
            "payload": {"app_name": "hello-agent"},
        },
    )
    assert source is not None
    assert source["label"] == "Agent app: Hello Agent"
    assert source["href"] == "/agent-apps/hello-agent"
