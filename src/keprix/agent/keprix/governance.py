"""Shared mutation gate checks for chat and agent loop paths."""

from __future__ import annotations

from keprix.agent.keprix.config import get_mutation_config
from keprix.governance.kill_relay import agent_stop_requested, workspace_locked
from keprix.governance.policy_receiver import get_policy_registry


def mutation_gates_open() -> tuple[bool, str | None]:
    config = get_mutation_config()
    if not config.enabled:
        return False, "mutation engine is disabled"
    if not get_policy_registry().feature_enabled("mutation_engine", default=True):
        return False, "mutation engine is blocked by governance policy"
    if agent_stop_requested():
        return False, "agent operations are halted by governance kill switch"
    if workspace_locked():
        return False, "workspace is read-only due to governance policy"
    return True, None
