"""Playbook node handlers for browser automation (Prompt 196)."""

from __future__ import annotations

from typing import Any

from keprix.browser.browser_profile import ProfileKind, get_profile_store
from keprix.browser.browser_skill import run_skill
from keprix.browser.harness import get_harness_manager
from keprix.browser.session_store import get_session_store, session_mode
from keprix.playbook.runtime.errors import PlaybookGraphError


async def browser_action_node(
    state: dict[str, Any],
    *,
    skill: str,
    objective: str | None = None,
    workspace_id: str | None = None,
    profile_kind: str = "disposable",
    approved: bool = True,
    url: str = "about:blank",
) -> dict[str, Any]:
    """Open a harness session and run a registered browser skill inside a playbook."""
    skill_name = (skill or "").strip()
    if not skill_name:
        raise PlaybookGraphError("browser_action requires skill")

    ws = (workspace_id or state.get("workspace_id") or "default").strip()
    merged_objective = (objective or state.get("objective") or "").strip() or f"Browser skill: {skill_name}"

    kind = ProfileKind.DISPOSABLE if profile_kind == "disposable" else ProfileKind.PERSISTENT
    profile = get_profile_store().create(
        workspace_id=ws,
        name=f"playbook-{skill_name}",
        kind=kind,
    )
    harness, record = get_harness_manager().open_session(
        workspace_id=ws,
        objective=merged_objective,
        url=url,
        profile_id=profile.id,
    )
    result = run_skill(skill_name, harness, {"approved": approved})
    mode = "dry_run" if result.get("dry_run") else session_mode(record)
    get_session_store().update_metadata(record.session_id, {"mode": mode, "skill": skill_name})

    new_state = dict(state)
    new_state["browser_session_id"] = harness.session_id
    new_state["browser_result"] = {
        "session_id": harness.session_id,
        "skill": skill_name,
        "mode": mode,
        "status": result.get("status"),
        "dry_run": bool(result.get("dry_run")),
        "result": result,
    }
    return new_state
