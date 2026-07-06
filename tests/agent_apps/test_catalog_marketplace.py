"""Marketplace catalog tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.agent_apps.catalog import list_catalog_templates, template_dir
from keprix.agent_apps.eval_runner import run_eval_suite
from keprix.agent_apps.registry import AgentAppRegistry
from keprix.agent_apps.routes import router as agent_apps_router
from keprix.api.auth import require_api_auth
from keprix.public_api.agent_runtime import AgentChatResult

CATALOG_IDS = ("daily-standup", "research-brief", "invoice-review")


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

    async def _noop_audit(*_args, **_kwargs) -> None:
        return None

    app.dependency_overrides[require_api_auth] = _fake_auth
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_run", _allow_entitlement)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install", _allow_entitlement)
    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install_catalog_template", _allow_entitlement)
    monkeypatch.setattr("keprix.agent_apps.routes.audit_log", _noop_audit)
    return TestClient(app)


@pytest.fixture()
def mock_catalog_llm(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    async def _fake(**kwargs):
        content = str(kwargs.get("messages", [{}])[-1].get("content", "")).lower()
        if "invoice" in content:
            text = "Invoice review summary with line items."
        elif "research" in content or "topic" in content:
            text = "Research brief with sections and citations placeholder."
        else:
            text = "Standup: shipped marketplace catalog tests."
        return AgentChatResult(
            final_response=text,
            session_id="agent-app:catalog-test",
            prompt_tokens=3,
            completion_tokens=5,
            total_tokens=8,
        )

    mock = AsyncMock(side_effect=_fake)
    monkeypatch.setattr("keprix.public_api.agent_runtime.run_agent_chat_completion", mock)
    return mock


def test_catalog_lists_three_templates() -> None:
    templates = list_catalog_templates()
    ids = {item["id"] for item in templates}
    assert ids >= set(CATALOG_IDS)


@pytest.mark.parametrize("template_id", CATALOG_IDS)
def test_catalog_template_has_required_files(template_id: str) -> None:
    source = template_dir(template_id)
    assert source is not None
    assert (source / "agent.yaml").exists()
    assert (source / "instructions.md").exists()
    assert (source / "README.md").exists()
    assert (source / "evals" / "basic.yaml").exists()
    assert any(source.glob("tools/*.yaml"))


@pytest.mark.parametrize("template_id", CATALOG_IDS)
def test_catalog_install_copies_files(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    template_id: str,
) -> None:
    from keprix.agent_apps import registry as registry_module
    from keprix.agent_apps.registry import get_agent_app_registry

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    response = client.post(f"/api/agent-apps/catalog/{template_id}/install")
    assert response.status_code == 200
    body = response.json()
    assert body["redirect"] == f"/agent-apps/{template_id}"
    app_dir = get_agent_app_registry().app_dir(template_id)
    assert app_dir is not None
    assert (app_dir / "agent.yaml").exists()
    assert (app_dir / "instructions.md").exists()


def test_catalog_lists_pro_locked_flag(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "keprix.agent_apps.routes.pro_templates_enabled",
        AsyncMock(return_value=False),
    )
    response = client.get("/api/agent-apps/catalog")
    assert response.status_code == 200
    templates = {item["id"]: item for item in response.json()["templates"]}
    assert templates["daily-standup"]["pro_locked"] is False
    assert templates["research-brief"]["pro_locked"] is True
    assert templates["invoice-review"]["pro_locked"] is True


def test_pro_template_install_returns_402(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "keprix.agent_apps.routes.pro_templates_enabled",
        AsyncMock(return_value=False),
    )

    async def _deny_pro(user_id: str, template_id: str) -> None:
        del user_id
        if template_id != "daily-standup":
            raise PermissionError("agent_apps.pro_templates")

    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install_catalog_template", _deny_pro)
    response = client.post("/api/agent-apps/catalog/research-brief/install")
    assert response.status_code == 402
    body = response.json()["detail"]
    assert body["detail"] == "agent_apps.pro_templates"


@pytest.mark.parametrize("template_id", CATALOG_IDS)
def test_catalog_eval_smoke(
    template_id: str,
    mock_catalog_llm: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del mock_catalog_llm
    source = template_dir(template_id)
    assert source is not None
    monkeypatch.setenv("KEPRIX_DEFAULT_PROVIDER", "deepseek")
    report = run_eval_suite(source)
    assert report["success"] is True
    assert report["passed"] >= 1
