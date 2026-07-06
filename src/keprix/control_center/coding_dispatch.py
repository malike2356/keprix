"""Dispatch control-center coding sessions to the code agent runner."""

from __future__ import annotations

from typing import Any

from keprix.code_agent.session_runner import CodingSessionRunner
from keprix.control_center.run_queue import complete_run, fail_run, start_run
from keprix.control_center.workspace_sessions import append_trace, update_session_status


async def start_coding_session_from_queue(
    *,
    run_id: str,
    session_id: str,
    objective: str,
    repo_path: str | None = None,
    workspace_id: str = "default",
    max_turns: int = 3,
) -> dict[str, Any]:
    """Execute a queued coding session for up to max_turns."""
    start_run(run_id)
    update_session_status(session_id, "active")
    runner = CodingSessionRunner()
    record = runner.create_session(
        workspace_id=workspace_id,
        objective=objective,
        repo_path=repo_path,
        control_center_session_id=session_id,
    )
    append_trace(session_id, "coding_dispatch_started", {"code_agent_session_id": record.id, "run_id": run_id})

    logs: list[str] = []
    try:
        for _ in range(max_turns):
            turn = runner.run_turn(record.id)
            logs.append(f"turn {turn.turn}: {turn.action} - {turn.summary}")
            if turn.session_status in {"completed", "failed"}:
                break
        final = runner.store.get(record.id)
        status = final.status if final else "failed"
        if status == "completed":
            update_session_status(session_id, "completed")
            complete_run(run_id, logs=logs)
        else:
            update_session_status(session_id, "active")
            complete_run(run_id, logs=logs + ["Session left active for resume"])
        return {"code_agent_session_id": record.id, "status": status, "turns": final.turn if final else 0}
    except Exception as exc:  # noqa: BLE001
        fail_run(run_id, logs=logs + [str(exc)])
        update_session_status(session_id, "failed")
        raise
