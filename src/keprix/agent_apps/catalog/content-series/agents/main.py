"""Content Series Generator entrypoint."""

from __future__ import annotations

from typing import Any

from keprix.agent_os.workflow_kanban import enqueue_workflow_steps
from keprix.agent_os.workflows.content_series import generate_content_series


def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    topic = str(form.get("topic") or input_text or "").strip()
    questions = str(form.get("audience_questions") or "")
    platforms_raw = str(form.get("platforms") or "linkedin,x,youtube,instagram,email")
    platforms = [p.strip() for p in platforms_raw.split(",") if p.strip()]
    result = generate_content_series(topic=topic, audience_questions=questions, platforms=platforms)
    board = enqueue_workflow_steps(
        workflow="content-series",
        title=result["topic"],
        steps=result.get("steps") or [],
        push_kanban=True,
    )
    result["kanban"] = board
    result["artifact"] = {**(result.get("artifact") or {}), "auto_skill": True, "board_id": board.get("board_id")}
    return result
