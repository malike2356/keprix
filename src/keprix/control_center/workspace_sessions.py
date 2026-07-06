"""Long-running workspace sessions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from keprix.control_center.agent_server_registry import get_server, requires_approval
from keprix.control_center.run_queue import enqueue_run
from keprix.control_center.store import get_control_center_store

SessionStatus = Literal["active", "paused", "stopped", "completed", "failed"]
TaskType = Literal["coding", "research", "browser", "analytics", "opportunity", "playbook", "custom"]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(
    *,
    server_id: str,
    task_type: TaskType,
    objective: str,
    playbook_id: str | None = None,
    owner: str = "admin",
) -> dict[str, Any]:
    store = get_control_center_store()
    server = get_server(server_id)
    if server is None:
        raise ValueError("Agent server not found")

    approval_needed = requires_approval(server.get("capabilities") or [], task_type)
    session = {
        "id": str(uuid.uuid4()),
        "server_id": server_id,
        "task_type": task_type,
        "objective": objective,
        "playbook_id": playbook_id,
        "status": "paused" if approval_needed else "active",
        "owner": owner,
        "trace_events": [{"type": "session_start", "at": _utcnow(), "payload": {"objective": objective}}],
        "artifacts": [],
        "requires_approval": approval_needed,
        "repo_path": repo_path,
        "workspace_id": workspace_id,
        "code_agent_session_id": None,
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }
    store.save_session(session)
    if auto_enqueue and task_type == "coding" and not approval_needed:
        run = enqueue_run(
            payload={
                "task_type": "coding",
                "session_id": session["id"],
                "objective": objective,
                "repo_path": repo_path,
                "workspace_id": workspace_id,
            },
            session_id=session["id"],
        )
        session["queued_run_id"] = run["id"]
        store.save_session(session)
    if approval_needed:
        store.save_approval(
            {
                "id": str(uuid.uuid4()),
                "session_id": session["id"],
                "reason": f"Destructive {task_type} task requires approval",
                "status": "pending",
                "created_at": _utcnow(),
            }
        )
    store.append_activity(
        {
            "type": "session_created",
            "message": f"Session {session['id'][:8]} started ({task_type})",
            "session_id": session["id"],
            "server_id": server_id,
        }
    )
    return session


def update_session_status(session_id: str, status: SessionStatus) -> dict[str, Any] | None:
    store = get_control_center_store()
    session = store.get_session(session_id)
    if session is None:
        return None
    session["status"] = status
    session["updated_at"] = _utcnow()
    session["trace_events"].append({"type": f"session_{status}", "at": _utcnow(), "payload": {}})
    store.save_session(session)
    store.append_activity(
        {
            "type": "session_status",
            "message": f"Session {session_id[:8]} -> {status}",
            "session_id": session_id,
        }
    )
    return session


def append_trace(session_id: str, event_type: str, payload: dict[str, Any] | None = None) -> None:
    store = get_control_center_store()
    session = store.get_session(session_id)
    if session is None:
        return
    session["trace_events"].append({"type": event_type, "at": _utcnow(), "payload": dict(payload or {})})
    session["updated_at"] = _utcnow()
    store.save_session(session)


def append_artifact(session_id: str, name: str, path: str, *, kind: str = "file") -> dict[str, Any]:
    store = get_control_center_store()
    session = store.get_session(session_id)
    artifact = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "name": name,
        "path": path,
        "kind": kind,
        "created_at": _utcnow(),
    }
    store.save_artifact(artifact)
    if session is not None:
        session["artifacts"].append(artifact)
        session["updated_at"] = _utcnow()
        store.save_session(session)
    return artifact


def list_sessions(*, status: str | None = None) -> list[dict[str, Any]]:
    sessions = get_control_center_store().list_sessions()
    if status:
        sessions = [session for session in sessions if session.get("status") == status]
    return sessions
