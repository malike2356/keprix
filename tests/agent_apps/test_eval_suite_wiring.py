"""Agent Apps eval suite wiring (prompt 186)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from keprix.agent_apps.eval_harness import AgentAppsEvalHarness
from keprix.agent_apps.registry import AgentAppRegistry


@pytest.fixture()
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentAppsEvalHarness:
    from keprix.agent_apps import registry as registry_module

    registry = AgentAppRegistry(base_dir=tmp_path / "registry")
    monkeypatch.setattr(registry_module, "_registry", registry)
    fixture = AgentAppsEvalHarness(registry)
    fixture.apply_route_mocks(monkeypatch)
    return fixture


def test_agent_apps_suite_file_present():
    suite_path = Path(__file__).resolve().parents[2] / "evals" / "suites" / "agent-apps" / "basics.yaml"
    assert suite_path.is_file()
    data = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    assert data["name"] == "agent_apps_basics"
    task_ids = {task["id"] for task in data["tasks"]}
    assert task_ids == {
        "catalog_lists_templates",
        "install_daily_standup",
        "readiness_endpoint",
        "run_returns_output",
        "usage_endpoint",
        "billing_402_on_limit",
    }


@pytest.mark.parametrize(
    "check",
    [
        "catalog_lists_templates",
        "install_daily_standup",
        "readiness_endpoint",
        "run_returns_output",
        "usage_endpoint",
        "billing_402_on_limit",
    ],
)
def test_agent_apps_wiring_checks(harness: AgentAppsEvalHarness, check: str) -> None:
    result = harness.run_wiring_check(check)
    assert result.get("blocked") is not True, result.get("output")
