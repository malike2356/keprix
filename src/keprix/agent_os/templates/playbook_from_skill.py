"""Playbook promotion template."""

from __future__ import annotations

from typing import Any


def playbook_document(skill_slug: str, *, name: str | None = None) -> dict[str, Any]:
    graph_id = (name or skill_slug).replace(" ", "-").lower()
    step_id = "run_skill"
    return {
        "id": graph_id,
        "name": name or f"{skill_slug} playbook",
        "entry": step_id,
        "steps": [
            {
                "id": step_id,
                "type": "agent_task",
                "prompt": f"Use the `{skill_slug}` skill to complete this workflow.",
                "skills": [skill_slug],
            }
        ],
        "edges": [],
    }
