"""Playbook integration for external review requests."""

from __future__ import annotations

from typing import Any

from keprix.review_gateway.service import create_review_request


async def run_review_request_step(
    *,
    workspace_id: str,
    config: dict[str, Any],
    playbook_run_id: str,
    step_id: str,
    context_variables: dict[str, Any],
    base_url: str = "http://localhost:8000",
) -> dict[str, Any]:
    artifact_content = config.get("artifact_content", "")
    if isinstance(artifact_content, str) and artifact_content.startswith("{{"):
        key = artifact_content.strip("{} ").strip()
        artifact_content = str(context_variables.get(key, artifact_content))
    req, _url_token = await create_review_request(
        workspace_id=workspace_id,
        title=config["title"],
        context_message=config.get("context_message", ""),
        artifact_type=config.get("artifact_type", "markdown"),
        artifact_content=str(artifact_content),
        artifact_url=str(config.get("artifact_url", "")),
        artifact_filename=str(config.get("artifact_filename", "")),
        reviewer_name=str(config["reviewer_name"]),
        reviewer_email=str(config["reviewer_email"]),
        allowed_actions=list(config.get("allowed_actions", ["approve", "reject"])),
        expires_in_hours=int(config.get("expires_in_hours", 48)),
        reminder_in_hours=config.get("reminder_in_hours"),
        playbook_run_id=playbook_run_id,
        playbook_step_id=step_id,
        base_url=base_url,
    )
    return {"status": "paused", "review_request_id": req.id}


def interpret_resume_action(action: str, note: str = "") -> dict[str, Any]:
    if action == "approve":
        return {"status": "success", "review_action": action, "reviewer_note": note}
    if action == "reject":
        return {"status": "failed", "error": f"Reviewer rejected: {note}", "review_action": action}
    return {"status": "paused_for_changes", "review_action": action, "reviewer_note": note}
