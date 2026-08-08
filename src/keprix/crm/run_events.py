"""Append-only CRM workflow run events and replay (prompt 509)."""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.crm.visual_contract import RUNTIME_STATES


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _store_path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "crm"
    except Exception:
        root = Path.home() / ".keprix" / "crm"
    root.mkdir(parents=True, exist_ok=True)
    return root / "workflow_runs.json"


def _load() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict[str, Any]) -> None:
    _store_path().write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _redact(detail: Any) -> Any:
    if isinstance(detail, dict):
        out = {}
        for k, v in detail.items():
            kl = str(k).lower()
            if any(s in kl for s in ("secret", "password", "token", "api_key", "authorization")):
                out[k] = "[redacted]"
            elif kl in {"email", "phone", "body"} and isinstance(v, str) and len(v) > 3:
                out[k] = v[:2] + "***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(detail, list):
        return [_redact(x) for x in detail]
    return detail


def create_run(
    workspace_id: str,
    *,
    workflow_id: str,
    workflow_version: int = 1,
    subject_type: str = "lead",
    subject_id: str | None = None,
    graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = _load()
    ws = data.setdefault(workspace_id, {})
    run_id = str(uuid.uuid4())
    run = {
        "id": run_id,
        "workspace_id": workspace_id,
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "status": "ready",
        "created_at": _now(),
        "updated_at": _now(),
        "cursor": 0,
        "events": [],
        "node_states": {},
        "graph_snapshot": copy.deepcopy(graph) if graph else None,
    }
    # Seed upcoming nodes from graph
    if graph:
        for node in graph.get("nodes") or []:
            run["node_states"][node["id"]] = {
                "state": "upcoming",
                "label": node.get("label") or node.get("type"),
                "attempts": [],
            }
    ws[run_id] = run
    data[workspace_id] = ws
    _save(data)
    append_event(
        workspace_id,
        run_id,
        node_id=None,
        state="ready",
        detail={"message": "Run created"},
    )
    return get_run(workspace_id, run_id) or run


def append_event(
    workspace_id: str,
    run_id: str,
    *,
    node_id: str | None,
    state: str,
    detail: dict[str, Any] | None = None,
    attempt: int = 1,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    if state not in RUNTIME_STATES and state not in {"started", "completed"}:
        # map aliases
        aliases = {"started": "active", "completed": "succeeded", "blocked": "approval_required"}
        state = aliases.get(state, state)
    data = _load()
    run = (data.get(workspace_id) or {}).get(run_id)
    if not run:
        raise LookupError(run_id)
    cursor = int(run.get("cursor") or 0) + 1
    event = {
        "id": str(uuid.uuid4()),
        "seq": cursor,
        "workspace_id": workspace_id,
        "workflow_id": run.get("workflow_id"),
        "workflow_version": run.get("workflow_version"),
        "run_id": run_id,
        "node_id": node_id,
        "subject_id": run.get("subject_id"),
        "attempt": attempt,
        "timestamp": _now(),
        "state": state,
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "detail": _redact(detail or {}),
    }
    run["events"].append(event)
    run["cursor"] = cursor
    run["updated_at"] = event["timestamp"]
    if node_id:
        ns = run.setdefault("node_states", {}).setdefault(
            node_id, {"state": "upcoming", "label": node_id, "attempts": []}
        )
        ns["state"] = state
        ns["attempts"].append(
            {
                "attempt": attempt,
                "state": state,
                "timestamp": event["timestamp"],
                "detail": event["detail"],
            }
        )
    # Honest run status from latest durable event
    if state in {"failed", "cancelled", "succeeded", "partially_succeeded", "paused", "waiting", "approval_required", "active", "suppressed"}:
        if state == "active" and run.get("status") in {"succeeded", "failed", "cancelled"}:
            pass
        else:
            run["status"] = state if state != "active" else "active"
    data[workspace_id][run_id] = run
    _save(data)
    return event


def get_run(workspace_id: str, run_id: str) -> dict[str, Any] | None:
    data = _load()
    run = (data.get(workspace_id) or {}).get(run_id)
    if not run:
        return None
    return copy.deepcopy(run)


def list_runs(workspace_id: str, *, workflow_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    data = _load()
    items = list((data.get(workspace_id) or {}).values())
    # skip internal keys
    items = [r for r in items if isinstance(r, dict) and r.get("id")]
    if workflow_id:
        items = [r for r in items if str(r.get("workflow_id")) == workflow_id]
    items.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return [copy.deepcopy(r) for r in items[:limit]]


def run_snapshot(workspace_id: str, run_id: str) -> dict[str, Any]:
    run = get_run(workspace_id, run_id)
    if not run:
        raise LookupError(run_id)
    return {
        "run": {
            "id": run["id"],
            "workspace_id": workspace_id,
            "workflow_id": run.get("workflow_id"),
            "workflow_version": run.get("workflow_version"),
            "status": run.get("status"),
            "subject_type": run.get("subject_type"),
            "subject_id": run.get("subject_id"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "cursor": run.get("cursor"),
        },
        "node_states": run.get("node_states") or {},
        "graph": run.get("graph_snapshot"),
        "timeline": [
            {
                "seq": e["seq"],
                "node_id": e.get("node_id"),
                "state": e.get("state"),
                "timestamp": e.get("timestamp"),
                "label": (run.get("node_states") or {}).get(str(e.get("node_id") or ""), {}).get("label")
                or e.get("state"),
            }
            for e in run.get("events") or []
        ],
        "animation_policy": {
            "only_on_durable_events": True,
            "no_fake_idle_loops": True,
            "respect_reduced_motion": True,
        },
    }


def run_events_since(workspace_id: str, run_id: str, *, cursor: int = 0) -> dict[str, Any]:
    run = get_run(workspace_id, run_id)
    if not run:
        raise LookupError(run_id)
    events = [e for e in (run.get("events") or []) if int(e.get("seq") or 0) > int(cursor)]
    # Dedup by seq
    seen: set[int] = set()
    deduped = []
    for e in events:
        seq = int(e["seq"])
        if seq in seen:
            continue
        seen.add(seq)
        deduped.append(e)
    return {
        "run_id": run_id,
        "cursor": run.get("cursor") or 0,
        "events": deduped,
        "snapshot_recommended": int(cursor) > 0 and len(deduped) == 0 and int(run.get("cursor") or 0) < int(cursor),
    }


def seed_demo_progression(workspace_id: str, run_id: str) -> dict[str, Any]:
    """Advance one honest step for UI testing; no external effects."""
    run = get_run(workspace_id, run_id)
    if not run:
        raise LookupError(run_id)
    graph = run.get("graph_snapshot") or {}
    nodes = list(graph.get("nodes") or [])
    states = run.get("node_states") or {}
    for node in nodes:
        st = str((states.get(node["id"]) or {}).get("state") or "upcoming")
        if st in {"upcoming", "ready"}:
            append_event(workspace_id, run_id, node_id=node["id"], state="active", detail={"message": "Node started"})
            return run_snapshot(workspace_id, run_id)
        if st == "active":
            nxt = "waiting" if node.get("family") in {"wait", "approval"} else "succeeded"
            if node.get("type") == "soft_wall_approval":
                nxt = "approval_required"
            append_event(workspace_id, run_id, node_id=node["id"], state=nxt, detail={"message": "Node progressed"})
            return run_snapshot(workspace_id, run_id)
        if st in {"waiting", "approval_required"}:
            append_event(
                workspace_id,
                run_id,
                node_id=node["id"],
                state="succeeded",
                detail={"message": "Gate cleared", "wake_at": None},
            )
            return run_snapshot(workspace_id, run_id)
    append_event(workspace_id, run_id, node_id=None, state="succeeded", detail={"message": "Run complete"})
    return run_snapshot(workspace_id, run_id)


def compare_runs(workspace_id: str, run_a: str, run_b: str) -> dict[str, Any]:
    a = get_run(workspace_id, run_a)
    b = get_run(workspace_id, run_b)
    if not a or not b:
        raise LookupError("run_not_found")
    a_states = a.get("node_states") or {}
    b_states = b.get("node_states") or {}
    node_ids = sorted(set(a_states) | set(b_states))
    divergent = []
    for nid in node_ids:
        sa = (a_states.get(nid) or {}).get("state")
        sb = (b_states.get(nid) or {}).get("state")
        if sa != sb:
            divergent.append({"node_id": nid, "a": sa, "b": sb})
    return {
        "run_a": run_a,
        "run_b": run_b,
        "divergent_nodes": divergent,
        "status_a": a.get("status"),
        "status_b": b.get("status"),
        "event_count_a": len(a.get("events") or []),
        "event_count_b": len(b.get("events") or []),
    }
