"""Map coding trajectory JSONL events to builder patch steps (Prompt 198)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.coding.trajectory import TrajectoryLogger

_EVENT_LABELS: dict[str, str] = {
    "issue_parsed": "Parse issue",
    "filemap_built": "Build file map",
    "patch_proposed": "Propose patch",
    "patch_applied": "Apply patch",
    "tests_run": "Run tests",
    "rollback": "Rollback changes",
    "error": "Error",
    "approval_required": "Approval required",
}


def read_trajectory_events(run_id: str) -> list[dict[str, Any]]:
    path = TrajectoryLogger(run_id=run_id).path
    if path is None or not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            import json

            events.append(json.loads(line))
    return events


def events_to_patch_steps(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        event_type = str(event.get("event") or "unknown")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        diff = payload.get("patch")
        if not isinstance(diff, str):
            diff = None
        steps.append(
            {
                "id": f"step-{index}",
                "event": event_type,
                "label": _EVENT_LABELS.get(event_type, event_type.replace("_", " ").title()),
                "timestamp": event.get("ts"),
                "diff": diff,
                "summary": _step_summary(event_type, payload),
                "needs_approval": event_type == "approval_required" or bool(payload.get("needs_approval")),
                "payload": payload,
            }
        )
    return steps


def load_patch_steps_for_run(run_id: str) -> list[dict[str, Any]]:
    return events_to_patch_steps(read_trajectory_events(run_id))


def append_trajectory_event(run_id: str, event_type: str, payload: dict[str, Any]) -> Path | None:
    logger = TrajectoryLogger(run_id=run_id)
    logger.log(event_type, payload)
    return logger.path


def _step_summary(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == "issue_parsed":
        return str(payload.get("title") or "Issue parsed")
    if event_type == "filemap_built":
        return f"{payload.get('packages', 0)} packages, {payload.get('tests', 0)} tests"
    if event_type == "patch_proposed":
        return f"{payload.get('edit_count', 0)} edits proposed"
    if event_type == "patch_applied":
        paths = payload.get("paths") or []
        return f"Applied to {len(paths)} file(s)"
    if event_type == "tests_run":
        passed = payload.get("passed")
        status = "passed" if passed else "failed"
        return f"Tests {status}"
    if event_type == "rollback":
        return str(payload.get("reason") or "Changes rolled back")
    if event_type == "approval_required":
        return str(payload.get("reason") or "Tier 3 approval required")
    if event_type == "error":
        return str(payload.get("message") or "Run failed")
    return event_type.replace("_", " ")
