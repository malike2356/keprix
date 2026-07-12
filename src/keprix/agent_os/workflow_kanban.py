"""Push workflow sub-steps onto the Keprix Kanban board (Prompt 270 Task 2.4)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix_constants import get_keprix_home

logger = logging.getLogger(__name__)


def _board_store_path() -> Path:
    path = get_keprix_home() / "agent-os" / "workflow-boards"
    path.mkdir(parents=True, exist_ok=True)
    return path


def enqueue_workflow_steps(
    *,
    workflow: str,
    title: str,
    steps: list[dict[str, Any]],
    push_kanban: bool = True,
) -> dict[str, Any]:
    """Create a visual task board for a workflow run.

    Always writes a lightweight JSON board under agent-os. When Kanban DB is
    available, also creates a parent task plus child tasks for unfinished steps.
    """
    board_id = f"wf-{uuid4().hex[:10]}"
    board = {
        "id": board_id,
        "workflow": workflow,
        "title": title,
        "columns": {
            "todo": [],
            "doing": [],
            "done": [],
        },
        "kanban_task_ids": [],
    }
    for step in steps:
        card = {
            "id": str(step.get("id") or uuid4().hex[:8]),
            "title": str(step.get("title") or step),
            "status": str(step.get("status") or "todo"),
        }
        column = card["status"] if card["status"] in board["columns"] else "todo"
        if column == "done":
            board["columns"]["done"].append(card)
        elif column in {"doing", "running", "in_progress"}:
            board["columns"]["doing"].append(card)
        else:
            board["columns"]["todo"].append(card)

    path = _board_store_path() / f"{board_id}.json"
    path.write_text(json.dumps(board, indent=2), encoding="utf-8")

    kanban_ids: list[str] = []
    if push_kanban:
        try:
            from keprix_cli import kanban_db

            with kanban_db.connect_closing() as conn:
                parent_id = kanban_db.create_task(
                    conn,
                    title=f"[{workflow}] {title}",
                    body=f"Agent OS workflow board {board_id}",
                    created_by="agent-os",
                    triage=True,
                    idempotency_key=f"agent-os:{board_id}",
                )
                kanban_ids.append(parent_id)
                for card in board["columns"]["todo"]:
                    child_id = kanban_db.create_task(
                        conn,
                        title=card["title"],
                        body=f"Workflow step `{card['id']}` for {workflow}",
                        created_by="agent-os",
                        parents=[parent_id],
                        idempotency_key=f"agent-os:{board_id}:{card['id']}",
                    )
                    kanban_ids.append(child_id)
            board["kanban_task_ids"] = kanban_ids
            path.write_text(json.dumps(board, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("Kanban push skipped: %s", exc)
            board["kanban_error"] = str(exc)

    return {
        "ok": True,
        "board_id": board_id,
        "path": str(path),
        "board": board,
        "kanban_task_ids": kanban_ids,
    }


def list_workflow_boards(limit: int = 20) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(_board_store_path().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return rows
