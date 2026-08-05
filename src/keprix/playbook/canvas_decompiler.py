"""Decompile playbook YAML documents into Visual Playbook Studio canvas JSON."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def decompile_playbook_document(
    parsed: dict[str, Any],
    *,
    layout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert a playbook YAML document into Studio canvas JSON."""
    steps = [step for step in list(parsed.get("steps") or []) if isinstance(step, dict)]
    edges = [edge for edge in list(parsed.get("edges") or []) if isinstance(edge, dict)]
    layout = layout or {}
    positions = dict(layout.get("positions") or {})
    if not positions:
        positions = auto_layout_nodes(steps, edges)

    entry = str(parsed.get("entry") or steps[0].get("id") if steps else "start")
    trigger_id = "trigger"
    if any(str(step.get("id") or "") == trigger_id for step in steps):
        trigger_id = "studio_trigger"

    nodes: list[dict[str, Any]] = [
        {
            "id": trigger_id,
            "type": "trigger",
            "position": dict(positions.get(trigger_id) or {"x": 80, "y": 120}),
            "data": {
                "label": "Trigger",
                "description": str(parsed.get("description") or ""),
            },
        }
    ]
    for step in steps:
        step_id = str(step.get("id") or "")
        nodes.append(
            {
                "id": step_id,
                "type": _canvas_type(str(step.get("type") or "agent_task")),
                "position": dict(positions.get(step_id) or {"x": 320, "y": 120 + len(nodes) * 120}),
                "data": _step_data(step),
            }
        )

    canvas_edges: list[dict[str, Any]] = []
    if entry:
        canvas_edges.append(
            {
                "id": f"e_{trigger_id}_{entry}",
                "source": trigger_id,
                "target": entry,
                "sourceHandle": None,
                "targetHandle": None,
                "data": {"when": None},
            }
        )
    for edge in edges:
        source = str(edge.get("from") or edge.get("source") or "")
        target = str(edge.get("to") or edge.get("target") or "")
        if not source or not target:
            continue
        when = edge.get("when")
        canvas_edges.append(
            {
                "id": f"e_{source}_{target}_{when or 'next'}",
                "source": source,
                "target": target,
                "sourceHandle": str(when) if when in {"true", "false"} else None,
                "targetHandle": None,
                "data": {"when": str(when) if when is not None else None},
            }
        )

    return {
        "schema_version": 1,
        "id": str(parsed.get("id") or "studio-playbook"),
        "name": str(parsed.get("name") or parsed.get("id") or "Studio playbook"),
        "description": str(parsed.get("description") or ""),
        "entry": trigger_id,
        "variables": list(parsed.get("variables") or []),
        "nodes": nodes,
        "edges": canvas_edges,
        "viewport": dict(layout.get("viewport") or {"x": 0, "y": 0, "zoom": 1}),
    }


def auto_layout_nodes(steps: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Return a simple layered DAG layout for backend decompile consistency."""
    step_ids = [str(step.get("id") or "") for step in steps if step.get("id")]
    adjacency: dict[str, list[str]] = defaultdict(list)
    indegree = {step_id: 0 for step_id in step_ids}
    for edge in edges:
        source = str(edge.get("from") or edge.get("source") or "")
        target = str(edge.get("to") or edge.get("target") or "")
        if source in indegree and target in indegree:
            adjacency[source].append(target)
            indegree[target] += 1

    roots = [step_id for step_id, count in indegree.items() if count == 0]
    levels: dict[str, int] = {}
    queue = deque((root, 1) for root in roots)
    while queue:
        current, level = queue.popleft()
        levels[current] = max(levels.get(current, 0), level)
        for target in adjacency.get(current, []):
            queue.append((target, level + 1))

    positions: dict[str, dict[str, int]] = {"trigger": {"x": 80, "y": 120}}
    buckets: dict[int, list[str]] = defaultdict(list)
    for step_id in step_ids:
        buckets[levels.get(step_id, 1)].append(step_id)
    for level, ids in buckets.items():
        for index, step_id in enumerate(ids):
            positions[step_id] = {"x": 80 + level * 260, "y": 80 + index * 150}
    return positions


def _canvas_type(step_type: str) -> str:
    if step_type in {"approval", "human_approval"}:
        return "human_approval"
    if step_type in {"agent_task", "http", "condition", "parallel", "artifact"}:
        return step_type
    if step_type == "wait":
        return "delay"
    return "agent_task"


def _step_data(step: dict[str, Any]) -> dict[str, Any]:
    step_type = str(step.get("type") or "agent_task")
    label = str(step.get("label") or step.get("name") or step.get("id") or "")
    if step_type == "http":
        return {
            "label": label,
            "url": str(step.get("url") or ""),
            "method": str(step.get("method") or "GET"),
            "headers": dict(step.get("headers") or {}),
            "body": step.get("body"),
            "connector_id": step.get("connector_id"),
        }
    if step_type == "condition":
        return {
            "label": label,
            "expression": str(step.get("expression") or ""),
            "trueLabel": "True",
            "falseLabel": "False",
        }
    if step_type in {"human_approval", "approval"}:
        return {
            "label": label,
            "message": str(step.get("message") or "Approval required"),
            "risk": str(step.get("risk") or "medium"),
            "summary": str(step.get("summary") or label),
        }
    if step_type == "parallel":
        config = dict(step.get("config") or {})
        return {"label": label, "tasks": list(config.get("tasks") or [])}
    if step_type == "artifact":
        config = dict(step.get("config") or {})
        return {
            "label": label,
            "name": str(config.get("name") or label),
            "content": config.get("content"),
            "from_key": config.get("from_key"),
        }
    return {
        "label": label,
        "prompt": str(step.get("prompt") or ""),
        "tools": list(step.get("tools") or []),
        "connector_id": step.get("connector_id"),
    }
