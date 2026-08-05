"""Compile docs-style playbook YAML into runtime graphs."""

from __future__ import annotations

from typing import Any

from keprix.playbook.runtime.errors import PlaybookGraphError
from keprix.playbook.runtime.graph import END, PlaybookGraph
from keprix.playbook.sdk_workflow import compile_workflow_spec


def compile_playbook_document(parsed: dict[str, Any]) -> PlaybookGraph:
    """Compile playbook YAML (``steps`` + ``edges``) into a ``PlaybookGraph``."""
    steps = list(parsed.get("steps") or [])
    if not steps:
        raise PlaybookGraphError("Playbook requires at least one step")

    runtime_steps: list[dict[str, Any]] = []
    condition_meta: dict[str, dict[str, str | None]] = {}

    for step in steps:
        if not isinstance(step, dict):
            raise PlaybookGraphError("Each step must be a mapping")
        step_id = str(step.get("id") or "")
        if not step_id:
            raise PlaybookGraphError("Each step requires an id")
        step_type = str(step.get("type") or "agent_task")
        runtime_steps.append(_map_yaml_step(step_id, step_type, step))
        if step_type == "condition":
            condition_meta[step_id] = {
                "on_true": str(step["on_true"]) if step.get("on_true") else None,
                "on_false": str(step["on_false"]) if step.get("on_false") else None,
            }

    edges = _normalize_edges(parsed, condition_meta)
    spec: dict[str, Any] = {
        "graph_id": str(parsed.get("id") or "playbook"),
        "steps": runtime_steps,
        "edges": edges,
    }
    if parsed.get("entry"):
        spec["entry"] = str(parsed["entry"])
    return compile_workflow_spec(spec)


def _map_yaml_step(step_id: str, step_type: str, step: dict[str, Any]) -> dict[str, Any]:
    if step_type == "human_approval":
        return {
            "id": step_id,
            "type": "approval",
            "config": {
                "message": str(step.get("message") or "Approval required"),
                "risk": step.get("risk") or "medium",
                "summary": step.get("summary") or step_id,
            },
        }
    if step_type == "condition":
        return {
            "id": step_id,
            "type": "condition",
            "config": {
                "expression": str(step.get("expression") or "false"),
            },
        }
    if step_type == "http":
        return {
            "id": step_id,
            "type": "http",
            "config": {
                "url": str(step.get("url") or ""),
                "method": str(step.get("method") or "GET"),
                "body": step.get("body"),
                "headers": dict(step.get("headers") or {}),
                "connector_id": step.get("connector_id"),
            },
        }
    if step_type == "agent_task":
        return {
            "id": step_id,
            "type": "agent_task",
            "config": {
                "prompt": str(step.get("prompt") or ""),
                "tools": list(step.get("tools") or []),
                "connector_id": step.get("connector_id"),
            },
        }
    if step_type == "branch":
        return {
            "id": step_id,
            "type": "branch",
            "config": dict(step.get("config") or step),
        }
    if step_type in {"task", "approval", "parallel", "artifact"}:
        return {"id": step_id, "type": step_type, "config": dict(step.get("config") or {})}
    return {
        "id": step_id,
        "type": "task",
        "config": {
            "key": f"{step_id}_output",
            "value": step_type,
            "message": str(step.get("prompt") or step.get("message") or step_id),
        },
    }


def _normalize_edges(
    parsed: dict[str, Any],
    condition_meta: dict[str, dict[str, str | None]],
) -> list[dict[str, Any]]:
    raw_edges = list(parsed.get("edges") or [])
    mapped: list[dict[str, Any]] = []

    for edge in raw_edges:
        if not isinstance(edge, dict):
            continue
        source = str(edge.get("from") or edge.get("source") or "")
        target = str(edge.get("to") or edge.get("target") or "")
        if not source or not target:
            continue
        mapped_edge: dict[str, Any] = {"from": source, "to": target}
        when = edge.get("when")
        if when is not None:
            mapped_edge["when"] = when
        elif source in condition_meta:
            meta = condition_meta[source]
            if meta.get("on_true") == target:
                mapped_edge["when"] = "true"
            elif meta.get("on_false") == target:
                mapped_edge["when"] = "false"
        mapped.append(mapped_edge)

    if not mapped:
        ordered = [str(step["id"]) for step in parsed.get("steps") or [] if step.get("id")]
        for index, step_id in enumerate(ordered):
            target = ordered[index + 1] if index + 1 < len(ordered) else END
            edge: dict[str, Any] = {"from": step_id, "to": target}
            if step_id in condition_meta:
                # Linear fallback cannot represent both branches; require explicit edges.
                raise PlaybookGraphError(
                    f"Condition step '{step_id}' requires explicit edges with on_true/on_false targets"
                )
            mapped.append(edge)

    for step_id, meta in condition_meta.items():
        has_true = any(
            edge["from"] == step_id and edge.get("when") == "true" for edge in mapped
        )
        has_false = any(
            edge["from"] == step_id and edge.get("when") == "false" for edge in mapped
        )
        if meta.get("on_true") and not has_true:
            mapped.append({"from": step_id, "to": meta["on_true"], "when": "true"})
        if meta.get("on_false") and not has_false:
            mapped.append({"from": step_id, "to": meta["on_false"], "when": "false"})

    return mapped
