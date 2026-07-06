"""Agent app billing entitlement tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.agent_apps.catalog import template_dir
from keprix.agent_apps.entitlements import (
    assert_can_install,
    assert_can_install_catalog_template,
    assert_can_run,
    assert_can_schedule,
    assert_can_webhook,
    entitlement_http_detail,
    reset_agent_apps_config_cache,
    usage_summary,
)
from keprix.agent_apps.registry import AgentAppRegistry, sample_app_dir
from keprix.agent_apps.routes import router as agent_apps_router
from keprix.api.auth import require_api_auth


@pytest.fixture(autouse=True)
def _reset_config_cache() -> None:
    reset_agent_apps_config_cache()


@pytest.fixture()
def registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentAppRegistry:
    from keprix.agent_apps import registry as registry_module

    reg = AgentAppRegistry(base_dir=tmp_path / "registry")
    monkeypatch.setattr(registry_module, "_registry", reg)
    return reg


@pytest.mark.asyncio
async def test_install_limit_blocks_at_capacity(registry: AgentAppRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "keprix.agent_apps.entitlements.resolve_user_plan",
        AsyncMock(return_value="community"),
    )
    monkeypatch.setattr("keprix.agent_apps.entitlements.agent_apps_enabled", AsyncMock(return_value=True))
    for template_id in ("daily-standup", "research-brief", "invoice-review"):
        source = template_dir(template_id)
        assert source is not None
        registry.install(source, source="template", source_id=template_id)
    with pytest.raises(PermissionError, match="max_installed"):
        await assert_can_install("user-1")


@pytest.mark.asyncio
async def test_pro_template_blocked_on_community(registry: AgentAppRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "keprix.agent_apps.entitlements.resolve_user_plan",
        AsyncMock(return_value="community"),
    )
    monkeypatch.setattr("keprix.agent_apps.entitlements.agent_apps_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr("keprix.agent_apps.entitlements.marketplace_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr("keprix.agent_apps.entitlements.pro_templates_enabled", AsyncMock(return_value=False))
    with pytest.raises(PermissionError, match="pro_templates"):
        await assert_can_install_catalog_template("user-1", "research-brief")


@pytest.mark.asyncio
async def test_run_limit_blocks_when_exhausted(registry: AgentAppRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "keprix.agent_apps.entitlements.resolve_user_plan",
        AsyncMock(return_value="community"),
    )
    monkeypatch.setattr("keprix.agent_apps.entitlements.agent_apps_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr("keprix.agent_apps.entitlements._count_billable_runs_this_month", lambda: 50)
    with pytest.raises(PermissionError, match="max_runs_per_month"):
        await assert_can_run("user-1")


@pytest.mark.asyncio
async def test_product_flag_disables_agent_apps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "keprix.agent_apps.entitlements._product_agent_apps_enabled",
        lambda: False,
    )
    with pytest.raises(PermissionError, match="agent_apps.enabled"):
        await assert_can_run("user-1")


@pytest.mark.asyncio
async def test_schedule_and_webhook_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("keprix.agent_apps.entitlements.agent_apps_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr("keprix.agent_apps.entitlements.scheduled_enabled", AsyncMock(return_value=False))
    with pytest.raises(PermissionError, match="scheduled"):
        await assert_can_schedule("user-1", "daily-standup")
    monkeypatch.setattr("keprix.agent_apps.entitlements.webhooks_enabled", AsyncMock(return_value=False))
    with pytest.raises(PermissionError, match="webhooks"):
        await assert_can_webhook("user-1")


@pytest.mark.asyncio
async def test_usage_summary_includes_features(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "keprix.agent_apps.entitlements.resolve_user_plan",
        AsyncMock(return_value="pro"),
    )
    monkeypatch.setattr("keprix.agent_apps.entitlements.agent_apps_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr("keprix.agent_apps.entitlements.marketplace_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr("keprix.agent_apps.entitlements.pro_templates_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr("keprix.agent_apps.entitlements.scheduled_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr("keprix.agent_apps.entitlements.webhooks_enabled", AsyncMock(return_value=False))
    monkeypatch.setattr("keprix.agent_apps.entitlements.publish_enabled", AsyncMock(return_value=False))
    monkeypatch.setattr("keprix.agent_apps.entitlements._count_billable_runs_this_month", lambda: 2)
    usage = await usage_summary("user-1")
    assert usage["plan"] == "pro"
    assert usage["features"]["scheduled"] is True
    assert usage["features"]["webhooks"] is False


def test_entitlement_http_detail_shape() -> None:
    payload = entitlement_http_detail(
        "agent_apps.max_runs_per_month",
        {"runs_this_month": 50, "runs_limit": 50},
    )
    assert payload["detail"] == "agent_apps.max_runs_per_month"
    assert "50" in payload["message"]
    assert payload["upgrade_url"] == "/pricing"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from keprix.agent_apps import registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    app = FastAPI()
    app.include_router(agent_apps_router)

    async def _fake_auth() -> str:
        return "test-user"

    app.dependency_overrides[require_api_auth] = _fake_auth
    return TestClient(app)


def test_install_route_returns_structured_402(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.agent_apps import registry as registry_module
    from keprix.agent_apps.registry import get_agent_app_registry

    monkeypatch.setattr(registry_module, "_registry", AgentAppRegistry(base_dir=tmp_path / "registry"))
    for index in range(3):
        get_agent_app_registry().install(
            template_dir(("daily-standup", "research-brief", "invoice-review")[index]),
            source="template",
            source_id=f"tpl-{index}",
        )

    async def _deny_install(_user_id: str, *, plan: str | None = None) -> None:
        del plan
        raise PermissionError("agent_apps.max_installed")

    monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install", _deny_install)
    monkeypatch.setattr(
        "keprix.agent_apps.routes.usage_summary",
        AsyncMock(
            return_value={
                "installed_count": 3,
                "installed_limit": 3,
                "runs_this_month": 0,
                "runs_limit": 50,
                "plan": "community",
            },
        ),
    )
    response = client.post(
        "/api/agent-apps/install/upload",
        files={"file": ("hello-agent.zip", b"not-a-real-zip", "application/zip")},
    )
    assert response.status_code == 402
    body = response.json()["detail"]
    assert body["detail"] == "agent_apps.max_installed"
    assert body["upgrade_url"] == "/pricing"
