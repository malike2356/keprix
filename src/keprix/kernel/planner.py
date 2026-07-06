"""Goal-based function and playbook planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.kernel.plugin_contract import KernelPlugin, PluginRegistry

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class PlanStep:
    plugin_name: str
    function_name: str
    reason: str
    risk_level: str
    cost_units: int
    output_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "function_name": self.function_name,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "cost_units": self.cost_units,
            "output_type": self.output_type,
        }


@dataclass
class PlanResult:
    goal: str
    allowed: bool
    steps: list[PlanStep] = field(default_factory=list)
    refused: list[dict[str, str]] = field(default_factory=list)
    total_cost: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "allowed": self.allowed,
            "steps": [step.to_dict() for step in self.steps],
            "refused": self.refused,
            "total_cost": self.total_cost,
        }


class KernelPlanner:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def plan(
        self,
        goal: str,
        *,
        permissions: set[str],
        max_risk: str = "medium",
        required_output_type: str | None = None,
        max_cost: int | None = None,
    ) -> PlanResult:
        steps: list[PlanStep] = []
        refused: list[dict[str, str]] = []
        total_cost = 0
        max_risk_value = RISK_ORDER.get(max_risk, 1)
        goal_lower = goal.lower()

        for plugin in self._sorted_plugins():
            for function in plugin.functions:
                if not self._permission_allows(function.permissions, permissions):
                    refused.append(
                        {
                            "plugin": plugin.name,
                            "function": function.name,
                            "reason": "missing permission",
                        }
                    )
                    continue
                if RISK_ORDER.get(function.risk_level, 0) > max_risk_value:
                    refused.append(
                        {
                            "plugin": plugin.name,
                            "function": function.name,
                            "reason": "risk too high",
                        }
                    )
                    continue
                if required_output_type and function.output_type != required_output_type:
                    continue
                if not self._matches_goal(goal_lower, plugin, function):
                    continue
                if max_cost is not None and total_cost + function.cost_units > max_cost:
                    refused.append(
                        {
                            "plugin": plugin.name,
                            "function": function.name,
                            "reason": "cost budget exceeded",
                        }
                    )
                    continue
                steps.append(
                    PlanStep(
                        plugin_name=plugin.name,
                        function_name=function.name,
                        reason=f"Matched goal `{goal}`",
                        risk_level=function.risk_level,
                        cost_units=function.cost_units,
                        output_type=function.output_type,
                    )
                )
                total_cost += function.cost_units

        return PlanResult(
            goal=goal,
            allowed=len(steps) > 0,
            steps=steps,
            refused=refused,
            total_cost=total_cost,
        )

    def _sorted_plugins(self) -> list[KernelPlugin]:
        return self._registry.all_plugins()

    @staticmethod
    def _permission_allows(required: list[str], granted: set[str]) -> bool:
        if not required:
            return True
        return set(required).issubset(granted)

    @staticmethod
    def _matches_goal(goal_lower: str, plugin: KernelPlugin, function: Any) -> bool:
        haystack = " ".join(
            [
                plugin.name,
                plugin.documentation,
                " ".join(plugin.capability_tags),
                function.name,
                function.description,
            ]
        ).lower()
        tokens = [token for token in goal_lower.split() if len(token) > 2]
        if not tokens:
            return True
        return any(token in haystack for token in tokens)
