"""In-process eval harness for Agent Apps wiring checks (prompt 186)."""

from __future__ import annotations

import json
from contextlib import ExitStack
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.agent_apps.catalog import list_catalog_templates, template_dir
from keprix.agent_apps.public_routes import router as agent_apps_public_router
from keprix.agent_apps.registry import AgentAppRegistry, get_agent_app_registry
from keprix.agent_apps.routes import router as agent_apps_router
from keprix.api.auth import require_api_auth


class AgentAppsEvalHarness:
    """FastAPI harness for agent app eval wiring checks."""

    def __init__(self, registry: AgentAppRegistry | None = None) -> None:
        self.registry = registry or get_agent_app_registry()
        app = FastAPI()
        app.include_router(agent_apps_router)
        app.include_router(agent_apps_public_router)

        async def _fake_auth() -> str:
            return "eval-user"

        app.dependency_overrides[require_api_auth] = _fake_auth
        self.client = TestClient(app)
        self._stack: ExitStack | None = None

    def start(self) -> None:
        if self._stack is not None:
            return

        async def _allow(*_args, **_kwargs) -> None:
            return None

        def _fake_run(*_args, **_kwargs):
            return {
                "app": "daily-standup",
                "version": "1.0.0",
                "runner": "web",
                "trace_id": "eval-trace",
                "result": {"output": "Standup summary for eval", "status": "ok"},
                "output": {"markdown": "Standup summary for eval"},
            }

        self._stack = ExitStack()
        self._stack.enter_context(patch("keprix.agent_apps.routes.assert_can_run", new=_allow))
        self._stack.enter_context(patch("keprix.agent_apps.routes.assert_can_install", new=_allow))
        self._stack.enter_context(
            patch("keprix.agent_apps.routes.assert_can_install_catalog_template", new=_allow)
        )
        self._stack.enter_context(patch("keprix.agent_apps.routes.assert_can_schedule", new=_allow))
        self._stack.enter_context(patch("keprix.agent_apps.routes.assert_can_webhook", new=_allow))
        self._stack.enter_context(patch("keprix.agent_apps.routes.audit_log", new=AsyncMock(return_value=None)))
        self._stack.enter_context(
            patch(
                "keprix.agent_apps.routes.usage_summary",
                new=AsyncMock(
                    return_value={
                        "runs_this_month": 0,
                        "runs_limit": 50,
                        "installed_count": 0,
                        "installed_limit": 3,
                        "plan": "community",
                        "features": {},
                    },
                ),
            )
        )
        self._stack.enter_context(patch("keprix.agent_apps.routes.run_web", new=_fake_run))

    def stop(self) -> None:
        if self._stack is not None:
            self._stack.close()
            self._stack = None

    def apply_route_mocks(self, monkeypatch: Any) -> None:
        """Test helper using pytest monkeypatch instead of ExitStack."""
        async def _allow(*_args, **_kwargs) -> None:
            return None

        monkeypatch.setattr("keprix.agent_apps.routes.assert_can_run", _allow)
        monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install", _allow)
        monkeypatch.setattr("keprix.agent_apps.routes.assert_can_install_catalog_template", _allow)
        monkeypatch.setattr("keprix.agent_apps.routes.assert_can_schedule", _allow)
        monkeypatch.setattr("keprix.agent_apps.routes.assert_can_webhook", _allow)
        monkeypatch.setattr("keprix.agent_apps.routes.audit_log", AsyncMock(return_value=None))
        monkeypatch.setattr(
            "keprix.agent_apps.routes.usage_summary",
            AsyncMock(
                return_value={
                    "runs_this_month": 0,
                    "runs_limit": 50,
                    "installed_count": 0,
                    "installed_limit": 3,
                    "plan": "community",
                    "features": {},
                },
            ),
        )
        monkeypatch.setattr(
            "keprix.agent_apps.routes.run_web",
            lambda *_args, **_kwargs: {
                "result": {"output": "Standup summary for eval", "status": "ok"},
                "output": {"markdown": "Standup summary for eval"},
            },
        )

    def run_wiring_check(self, check: str) -> dict[str, Any]:
        self.start()
        handlers = {
            "catalog_lists_templates": self._check_catalog,
            "install_daily_standup": self._check_install,
            "readiness_endpoint": self._check_readiness,
            "run_returns_output": self._check_run,
            "usage_endpoint": self._check_usage,
            "billing_402_on_limit": self._check_billing_402,
        }
        handler = handlers.get(check)
        if handler is None:
            return {"output": f"unknown wiring_check: {check}", "blocked": True}
        return handler()

    def _check_catalog(self) -> dict[str, Any]:
        templates = list_catalog_templates()
        ids = [item["id"] for item in templates]
        ok = "daily-standup" in ids and len(ids) >= 3
        return {"output": json.dumps({"template_ids": ids}), "blocked": not ok}

    def _check_install(self) -> dict[str, Any]:
        source = template_dir("daily-standup")
        if source is None:
            return {"output": "", "blocked": True}
        installed = self.registry.install(source, source="template", source_id="daily-standup")
        ok = installed.get("name") == "daily-standup"
        return {"output": json.dumps({"name": installed["name"]}), "blocked": not ok}

    def _check_readiness(self) -> dict[str, Any]:
        self._ensure_installed()
        response = self.client.get("/api/agent-apps/daily-standup/readiness")
        body = response.json()
        ok = response.status_code == 200 and "ready" in body
        return {"output": json.dumps(body), "blocked": not ok}

    def _check_run(self) -> dict[str, Any]:
        self._ensure_installed()
        response = self.client.post(
            "/api/agent-apps/daily-standup/run",
            json={"inputs": {"focus": "eval"}, "runner": "web"},
        )
        body = response.json()
        ok = response.status_code == 200 and bool(body.get("output") or body.get("result"))
        return {"output": json.dumps(body), "blocked": not ok}

    def _check_usage(self) -> dict[str, Any]:
        response = self.client.get("/api/agent-apps/usage")
        body = response.json()
        ok = response.status_code == 200 and "runs_this_month" in body
        return {"output": json.dumps(body), "blocked": not ok}

    def _check_billing_402(self) -> dict[str, Any]:
        async def _deny(_user: str, *_args, **_kwargs) -> None:
            raise PermissionError("agent_apps.max_runs_per_month")

        self._ensure_installed()
        with patch("keprix.agent_apps.routes.assert_can_run", new=_deny):
            response = self.client.post(
                "/api/agent-apps/daily-standup/run",
                json={"inputs": {}, "runner": "web"},
            )
        detail = response.json().get("detail")
        ok = response.status_code == 402 and isinstance(detail, dict) and detail.get("upgrade_url") == "/pricing"
        return {"output": json.dumps(response.json()), "blocked": not ok}

    def _ensure_installed(self) -> None:
        if self.registry.get("daily-standup") is None:
            source = template_dir("daily-standup")
            if source is not None:
                self.registry.install(source, source="template", source_id="daily-standup")


def build_agent_apps_executor(harness: AgentAppsEvalHarness | None = None):
    fixture = harness or AgentAppsEvalHarness()

    def executor(task: Any) -> dict[str, Any]:
        check = str((task.metadata or {}).get("wiring_check") or task.id)
        payload = fixture.run_wiring_check(check)
        if payload.get("blocked"):
            payload["output"] = payload.get("output") or f"failed:{check}"
        return payload

    return executor
