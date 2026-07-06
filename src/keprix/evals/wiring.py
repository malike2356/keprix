"""Task executors for eval suites that use wiring_check metadata."""

from __future__ import annotations

from typing import Any

from keprix.agent_apps.eval_harness import AgentAppsEvalHarness, build_agent_apps_executor
from keprix.evals.registry import EvalTask

_AGENT_APP_CHECKS = {
    "catalog_lists_templates",
    "install_daily_standup",
    "readiness_endpoint",
    "run_returns_output",
    "usage_endpoint",
    "billing_402_on_limit",
}

_harness: AgentAppsEvalHarness | None = None


def suite_uses_agent_apps_wiring(suite_name: str) -> bool:
    return suite_name == "agent_apps_basics"


def wiring_executor_for_suite(suite_name: str):
    if not suite_uses_agent_apps_wiring(suite_name):
        return None
    global _harness
    if _harness is None:
        _harness = AgentAppsEvalHarness()
    return build_agent_apps_executor(_harness)


def wiring_executor_for_task(task: EvalTask):
    check = str((task.metadata or {}).get("wiring_check") or "")
    if check in _AGENT_APP_CHECKS:
        global _harness
        if _harness is None:
            _harness = AgentAppsEvalHarness()
        return build_agent_apps_executor(_harness)
    return None
