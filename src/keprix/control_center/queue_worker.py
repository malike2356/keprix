"""Background worker for control center run queue."""

from __future__ import annotations

from typing import Any

from keprix.control_center.coding_dispatch import start_coding_session_from_queue
from keprix.control_center.run_queue import list_queue
from keprix.playbook.runtime.runner import PlaybookRunner


async def process_queued_runs(*, limit: int = 5) -> list[dict[str, Any]]:
    """Process queued control-center runs (coding sessions and playbooks)."""
    results: list[dict[str, Any]] = []
    queued = list_queue(status="queued")[:limit]
    for item in queued:
        payload = item.get("payload") or {}
        task_type = payload.get("task_type") or payload.get("kind")
        run_id = str(item["id"])
        try:
            if task_type == "coding":
                result = await start_coding_session_from_queue(
                    run_id=run_id,
                    session_id=str(payload.get("session_id") or item.get("session_id") or ""),
                    objective=str(payload.get("objective") or "Coding task"),
                    repo_path=payload.get("repo_path"),
                    workspace_id=str(payload.get("workspace_id") or "default"),
                    max_turns=int(payload.get("max_turns") or 3),
                )
                results.append({"run_id": run_id, "task_type": "coding", "result": result})
                continue

            playbook_id = payload.get("playbook_id")
            if playbook_id:
                from keprix.playbook.runtime.graph import PlaybookGraph

                graph = PlaybookGraph(str(playbook_id))
                runner = PlaybookRunner(graph.compile())
                run = await runner.execute_inline(dict(payload.get("initial_state") or {}))
                from keprix.control_center.run_queue import complete_run, start_run

                start_run(run_id)
                complete_run(run_id, logs=[f"playbook {playbook_id} status={run.status.value}"])
                results.append({"run_id": run_id, "task_type": "playbook", "status": run.status.value})
                continue

            from keprix.control_center.run_queue import fail_run

            fail_run(run_id, logs=[f"Unsupported queue payload: {task_type or 'unknown'}"])
            results.append({"run_id": run_id, "error": "unsupported payload"})
        except Exception as exc:  # noqa: BLE001
            results.append({"run_id": run_id, "error": str(exc)})
    return results
