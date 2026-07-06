"""Playbook node handlers for builder self-coding jobs (Prompt 198)."""

from __future__ import annotations

from typing import Any

from keprix.backend.builder.build_agent import start_build_job
from keprix.backend.builder.registry import get_project_registry
from keprix.backend.builder.store import get_builder_store
from keprix.playbook.runtime.errors import PlaybookGraphError


async def self_coding_job_node(
    state: dict[str, Any],
    *,
    project_id: str,
    instruction: str | None = None,
) -> dict[str, Any]:
    """Start a builder job and store its id in playbook state."""
    normalized = (project_id or "").strip()
    if not normalized:
        raise PlaybookGraphError("self_coding_job requires project_id")

    project = get_project_registry().get_project(normalized)
    if project is None:
        raise PlaybookGraphError(f"Unknown builder project: {normalized}")

    task = (instruction or state.get("instruction") or state.get("objective") or "").strip()
    if not task:
        raise PlaybookGraphError("self_coding_job requires instruction")

    job = get_builder_store().create_job(
        {
            "project_id": normalized,
            "job_type": "playbook-self-coding",
            "instruction": task,
        }
    )
    start_build_job(job["id"])

    new_state = dict(state)
    new_state["builder_job_id"] = job["id"]
    new_state["builder_project_id"] = normalized
    new_state["builder_result"] = {"status": "pending", "job_id": job["id"]}
    return new_state
