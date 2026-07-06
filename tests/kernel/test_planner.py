"""Planner permission tests."""

from keprix.kernel.planner import KernelPlanner
from keprix.kernel.plugin_contract import get_plugin_registry


def test_planner_refuses_tools_outside_permissions() -> None:
    planner = KernelPlanner(get_plugin_registry())
    denied = planner.plan("greet the operator", permissions=set())
    assert denied.allowed is False
    assert denied.refused
    allowed = planner.plan("greet the operator", permissions={"memory.read"})
    assert allowed.allowed is True
    assert allowed.steps[0].function_name == "greet"


def test_planner_respects_risk_budget() -> None:
    planner = KernelPlanner(get_plugin_registry())
    result = planner.plan("greet", permissions={"memory.read"}, max_risk="low")
    assert result.allowed is True
