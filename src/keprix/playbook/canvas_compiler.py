"""Compile Visual Playbook Studio canvas JSON into playbook YAML documents."""

from __future__ import annotations

import os
import re
from collections import defaultdict, deque
from typing import Any

from keprix.playbook.yaml_compiler import compile_playbook_document

STEP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
CANVAS_NODE_TYPES = {
    "trigger",
    "agent_task",
    "http",
    "condition",
    "human_approval",
    "parallel",
    "artifact",
    "delay",
}
APPROVAL_RISKS = {"low", "medium", "high"}


def compile_canvas_document(canvas: dict[str, Any]) -> dict[str, Any]:
    """Compile Studio canvas JSON into a runtime-clean playbook YAML document."""
    errors = validate_canvas_document(canvas)
    hard_errors = [error for error in errors if error.get("severity") != "warning"]
    if hard_errors:
        raise CanvasCompileError(hard_errors)

    steps, edges, entry_id = canvas_to_yaml_steps(canvas)
    doc: dict[str, Any] = {
        "id": str(canvas.get("id") or "studio-playbook"),
        "name": str(canvas.get("name") or canvas.get("id") or "Studio playbook"),
        "description": str(canvas.get("description") or ""),
        "entry": entry_id,
        "variables": list(canvas.get("variables") or []),
        "steps": steps,
        "edges": edges,
    }
    compile_playbook_document(doc)
    return doc


def validate_canvas_document(canvas: dict[str, Any]) -> list[dict[str, str]]:
    """Return structured compile errors and warnings for a Studio canvas document."""
    errors: list[dict[str, str]] = []
    nodes = _nodes(canvas)
    edges = _edges(canvas)
    seen: set[str] = set()
    ids: set[str] = set()

    for node in nodes:
        node_id = str(node.get("id") or "")
        node_type = str(node.get("type") or "")
        if node_id in seen:
            errors.append(_error("duplicate_node_id", f"Duplicate step id '{node_id}'", node_id))
        seen.add(node_id)
        ids.add(node_id)
        if not STEP_ID_RE.match(node_id):
            errors.append(
                _error("invalid_step_id", f"Step id '{node_id}' must be snake_case", node_id)
            )
        if node_type not in CANVAS_NODE_TYPES:
            errors.append(_error("unsupported_node_type", f"Unsupported node type '{node_type}'", node_id))

    trigger_nodes = [node for node in nodes if node.get("type") == "trigger"]
    if len(trigger_nodes) > 1:
        errors.append(_error("duplicate_trigger", "Studio v0 supports exactly one trigger"))

    entry_id = _entry_id(canvas, nodes, edges)
    if not entry_id:
        errors.append(_error("missing_entry", "No trigger or entry node found"))
    elif entry_id not in ids:
        errors.append(_error("missing_entry", f"Entry node '{entry_id}' was not found", entry_id))

    incoming = defaultdict(int)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in ids:
            errors.append(_error("unknown_edge_source", f"Unknown edge source '{source}'", source))
        if target not in ids:
            errors.append(_error("unknown_edge_target", f"Unknown edge target '{target}'", target))
        incoming[target] += 1
        outgoing[source].append(edge)

    for node in nodes:
        node_id = str(node.get("id") or "")
        node_type = str(node.get("type") or "")
        data = dict(node.get("data") or {})
        if node_type == "trigger":
            if incoming[node_id]:
                errors.append(_error("trigger_has_incoming", f"Trigger '{node_id}' cannot have incoming edges", node_id))
            if not outgoing[node_id]:
                errors.append(_error("trigger_missing_outgoing", f"Trigger '{node_id}' needs an outgoing edge", node_id))
            continue
        if node_type == "agent_task" and not str(data.get("prompt") or "").strip():
            errors.append(_error("empty_agent_prompt", f"Agent task '{node_id}' requires a prompt", node_id))
        if node_type == "http" and not str(data.get("url") or "").strip():
            errors.append(_error("http_missing_url", f"HTTP step '{node_id}' requires url", node_id))
        if node_type == "condition":
            whens = {_edge_when(edge) for edge in outgoing.get(node_id, [])}
            if not {"true", "false"}.issubset(whens):
                errors.append(
                    _error(
                        "condition_missing_branches",
                        f"Condition '{node_id}' needs true and false outgoing edges",
                        node_id,
                    )
                )
            if not str(data.get("expression") or "").strip():
                errors.append(_error("condition_missing_expression", f"Condition '{node_id}' requires expression", node_id))
        if node_type == "human_approval" and str(data.get("risk") or "medium") not in APPROVAL_RISKS:
            errors.append(_error("invalid_approval_risk", f"Approval '{node_id}' risk must be low, medium, or high", node_id))

    if _has_cycle(nodes, edges):
        errors.append(_error("cycle_detected", "Canvas graph must be acyclic"))

    if entry_id:
        reachable = _reachable(entry_id, edges)
        for node in nodes:
            node_id = str(node.get("id") or "")
            if node_id not in reachable:
                errors.append(
                    _warning("orphan_node", f"Node '{node_id}' is not reachable from entry", node_id)
                )

    if os.environ.get("KEPRIX_STUDIO_STRICT_TOOLS") == "1":
        for node in nodes:
            if node.get("type") != "agent_task":
                continue
            for tool in list(dict(node.get("data") or {}).get("tools") or []):
                if not isinstance(tool, str) or not tool.strip():
                    errors.append(_error("invalid_tool_name", f"Agent task '{node.get('id')}' has invalid tool name"))

    return errors


def canvas_to_yaml_steps(canvas: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """Return ``(steps, edges, entry_id)`` for a Studio canvas document."""
    nodes = _nodes(canvas)
    edges = _edges(canvas)
    entry_id = _entry_id(canvas, nodes, edges)
    trigger_ids = {str(node.get("id") or "") for node in nodes if node.get("type") == "trigger"}

    steps: list[dict[str, Any]] = []
    for node in nodes:
        node_type = str(node.get("type") or "")
        node_id = str(node.get("id") or "")
        if node_type == "trigger":
            continue
        step = _node_to_step(node_id, node_type, dict(node.get("data") or {}), edges)
        steps.append(step)

    yaml_edges: list[dict[str, Any]] = []
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source in trigger_ids:
            continue
        yaml_edge: dict[str, Any] = {"from": source, "to": target}
        when = _edge_when(edge)
        if when:
            yaml_edge["when"] = when
        yaml_edges.append(yaml_edge)

    if entry_id in trigger_ids:
        outgoing = [edge for edge in edges if str(edge.get("source") or "") == entry_id]
        entry_id = str(outgoing[0].get("target") or "") if outgoing else None

    return steps, yaml_edges, entry_id


class CanvasCompileError(ValueError):
    """Raised when a canvas cannot be compiled."""

    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("Canvas compile failed")
        self.errors = errors


def _node_to_step(
    node_id: str,
    node_type: str,
    data: dict[str, Any],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    label = str(data.get("label") or node_id)
    if node_type == "agent_task":
        return {
            "id": node_id,
            "type": "agent_task",
            "label": label,
            "prompt": str(data.get("prompt") or ""),
            "tools": [str(tool) for tool in list(data.get("tools") or [])],
            "connector_id": data.get("connector_id"),
        }
    if node_type == "http":
        return {
            "id": node_id,
            "type": "http",
            "label": label,
            "url": str(data.get("url") or ""),
            "method": str(data.get("method") or "GET").upper(),
            "headers": dict(data.get("headers") or {}),
            "body": data.get("body"),
            "connector_id": data.get("connector_id"),
        }
    if node_type == "condition":
        step: dict[str, Any] = {
            "id": node_id,
            "type": "condition",
            "label": label,
            "expression": str(data.get("expression") or ""),
        }
        for edge in edges:
            if str(edge.get("source") or "") != node_id:
                continue
            when = _edge_when(edge)
            if when == "true":
                step["on_true"] = str(edge.get("target") or "")
            elif when == "false":
                step["on_false"] = str(edge.get("target") or "")
        return step
    if node_type == "human_approval":
        return {
            "id": node_id,
            "type": "human_approval",
            "label": label,
            "message": str(data.get("message") or "Approval required"),
            "risk": str(data.get("risk") or "medium"),
            "summary": str(data.get("summary") or label),
        }
    if node_type == "parallel":
        return {
            "id": node_id,
            "type": "parallel",
            "label": label,
            "config": {"tasks": list(data.get("tasks") or [])},
        }
    if node_type == "artifact":
        return {
            "id": node_id,
            "type": "artifact",
            "label": label,
            "config": {
                "name": str(data.get("name") or label),
                "content": data.get("content"),
                "from_key": data.get("from_key"),
            },
        }
    if node_type == "delay":
        return {
            "id": node_id,
            "type": "task",
            "label": label,
            "config": {
                "message": str(data.get("message") or "Delay placeholder"),
            },
        }
    return {"id": node_id, "type": node_type, "label": label}


def _nodes(canvas: dict[str, Any]) -> list[dict[str, Any]]:
    return [node for node in list(canvas.get("nodes") or []) if isinstance(node, dict)]


def _edges(canvas: dict[str, Any]) -> list[dict[str, Any]]:
    return [edge for edge in list(canvas.get("edges") or []) if isinstance(edge, dict)]


def _entry_id(
    canvas: dict[str, Any],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> str | None:
    triggers = [str(node.get("id") or "") for node in nodes if node.get("type") == "trigger"]
    if len(triggers) == 1:
        return triggers[0]
    explicit = canvas.get("entry")
    if isinstance(explicit, str) and explicit:
        return explicit
    targets = {str(edge.get("target") or "") for edge in edges}
    roots = [str(node.get("id") or "") for node in nodes if str(node.get("id") or "") not in targets]
    return roots[0] if len(roots) == 1 else None


def _edge_when(edge: dict[str, Any]) -> str | None:
    data = dict(edge.get("data") or {})
    when = data.get("when", edge.get("when", edge.get("sourceHandle")))
    if when is None or when == "":
        return None
    if isinstance(when, bool):
        return "true" if when else "false"
    return str(when).lower() if str(when).lower() in {"true", "false"} else str(when)


def _has_cycle(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> bool:
    ids = {str(node.get("id") or "") for node in nodes}
    indegree = {node_id: 0 for node_id in ids}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in ids}
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in ids or target not in ids:
            continue
        adjacency[source].append(target)
        indegree[target] += 1
    queue = deque(node_id for node_id, count in indegree.items() if count == 0)
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return visited != len(ids)


def _reachable(entry_id: str, edges: list[dict[str, Any]]) -> set[str]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[str(edge.get("source") or "")].append(str(edge.get("target") or ""))
    seen = {entry_id}
    queue = deque([entry_id])
    while queue:
        current = queue.popleft()
        for target in adjacency.get(current, []):
            if target and target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def _error(code: str, message: str, node_id: str | None = None) -> dict[str, str]:
    payload = {"code": code, "message": message, "severity": "error"}
    if node_id:
        payload["node_id"] = node_id
    return payload


def _warning(code: str, message: str, node_id: str | None = None) -> dict[str, str]:
    payload = _error(code, message, node_id)
    payload["severity"] = "warning"
    return payload
