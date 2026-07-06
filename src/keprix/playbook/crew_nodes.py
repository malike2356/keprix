"""Playbook node handlers for agent team crews (Prompt 195)."""

from __future__ import annotations

from typing import Any

from keprix.playbook.runtime.errors import PlaybookGraphError
from keprix.playbook.runtime.runner import PlaybookRunner
from keprix.teams.registry import team_registry


async def crew_execute_node(
    state: dict[str, Any],
    *,
    team_id: str,
    objective: str | None = None,
) -> dict[str, Any]:
    """Run a registered agent team inside a playbook graph node."""
    normalized = (team_id or "").strip()
    if not normalized:
        raise PlaybookGraphError("crew_execute requires team_id")

    entry = team_registry.get(normalized)
    if entry is None:
        raise PlaybookGraphError(f"Unknown agent team: {normalized}")

    merged = dict(state)
    merged["objective"] = (objective or merged.get("objective") or "").strip() or "Run crew flow"

    compiled = entry.flow.compile_to_playbook(entry.crew).compile()
    run = await PlaybookRunner(compiled).execute_inline(merged)

    new_state = dict(state)
    new_state.update(run.state)
    new_state["crew_result"] = {
        "team_id": normalized,
        "status": run.status.value,
        "objective": merged["objective"],
        "task_results": run.state.get("task_results", {}),
    }
    return new_state
