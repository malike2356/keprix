"""Import n8n workflow JSON into Studio canvas documents."""

from __future__ import annotations

import re
from typing import Any


def n8n_workflow_to_canvas(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert n8n workflow JSON into a Studio canvas document."""
    nodes = [node for node in list(payload.get("nodes") or []) if isinstance(node, dict)]
    connections = payload.get("connections") if isinstance(payload.get("connections"), dict) else {}
    warnings = n8n_to_canvas_warnings(payload)
    name_to_id: dict[str, str] = {}
    canvas_nodes: list[dict[str, Any]] = []

    for index, node in enumerate(nodes):
        node_type = str(node.get("type") or "")
        mapped = _map_node_type(node_type)
        if mapped is None:
            continue
        node_name = str(node.get("name") or f"node_{index}")
        node_id = _snake(node_name, fallback=f"node_{index}")
        name_to_id[node_name] = node_id
        position = _position(node, index)
        data = _node_data(mapped, node)
        canvas_nodes.append({"id": node_id, "type": mapped, "position": position, "data": data})

    canvas_edges: list[dict[str, Any]] = []
    for source_name, outputs in connections.items():
        source = name_to_id.get(source_name)
        if not source or not isinstance(outputs, dict):
            continue
        main = outputs.get("main") or []
        if not isinstance(main, list):
            continue
        for output_index, rows in enumerate(main):
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                target = name_to_id.get(str(row.get("node") or ""))
                if not target:
                    continue
                when = None
                if _node_type_by_name(nodes, source_name) in {"n8n-nodes-base.if", "n8n-nodes-base.switch"}:
                    when = "true" if output_index == 0 else "false"
                canvas_edges.append(
                    {
                        "id": f"e_{source}_{target}_{when or 'next'}",
                        "source": source,
                        "target": target,
                        "sourceHandle": when,
                        "targetHandle": None,
                        "data": {"when": when},
                    }
                )

    workflow_name = str(payload.get("name") or "Imported n8n workflow")
    return {
        "schema_version": 1,
        "id": _snake(workflow_name, fallback="imported_n8n_workflow"),
        "name": workflow_name,
        "description": "Imported from n8n. Review warnings before running.",
        "entry": next((node["id"] for node in canvas_nodes if node["type"] == "trigger"), None),
        "nodes": canvas_nodes,
        "edges": canvas_edges,
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "import_warnings": warnings,
    }


def n8n_to_canvas_warnings(payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for node in list(payload.get("nodes") or []):
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type") or "")
        node_name = str(node.get("name") or "node")
        if node_type == "n8n-nodes-base.switch":
            warnings.append(f"Switch node '{node_name}' imported using first true/false-style rule only")
        elif _map_node_type(node_type) is None:
            warnings.append(f"Skipped unsupported n8n node '{node_name}' ({node_type})")
    return warnings


def _map_node_type(node_type: str) -> str | None:
    if node_type in {"n8n-nodes-base.manualTrigger", "n8n-nodes-base.scheduleTrigger"}:
        return "trigger"
    if node_type == "@n8n/n8n-nodes-langchain.agent":
        return "agent_task"
    if node_type == "n8n-nodes-base.httpRequest":
        return "http"
    if node_type in {"n8n-nodes-base.if", "n8n-nodes-base.switch"}:
        return "condition"
    if node_type in {"n8n-nodes-base.slack", "n8n-nodes-base.discord", "n8n-nodes-base.telegram"}:
        return "agent_task"
    return None


def _node_data(mapped_type: str, node: dict[str, Any]) -> dict[str, Any]:
    parameters = node.get("parameters") if isinstance(node.get("parameters"), dict) else {}
    label = str(node.get("name") or mapped_type)
    if mapped_type == "trigger":
        return {"label": label, "description": str(parameters.get("rule") or "")}
    if mapped_type == "http":
        return {
            "label": label,
            "url": str(parameters.get("url") or ""),
            "method": str(parameters.get("method") or parameters.get("requestMethod") or "GET").upper(),
            "headers": {},
            "body": parameters.get("body"),
        }
    if mapped_type == "condition":
        expression = str(parameters.get("conditions") or parameters.get("rules") or "true")
        return {"label": label, "expression": expression, "trueLabel": "True", "falseLabel": "False"}
    return {
        "label": label,
        "prompt": f"Review imported n8n node '{label}' and replace with Keprix tools.",
        "tools": [],
    }


def _position(node: dict[str, Any], index: int) -> dict[str, int]:
    raw = node.get("position")
    if isinstance(raw, list) and len(raw) >= 2:
        return {"x": int(raw[0]), "y": int(raw[1])}
    return {"x": 80 + index * 260, "y": 120}


def _snake(value: str, *, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not slug or not re.match(r"^[a-z]", slug):
        slug = fallback
    return slug[:64]


def _node_type_by_name(nodes: list[dict[str, Any]], name: str) -> str:
    for node in nodes:
        if str(node.get("name") or "") == name:
            return str(node.get("type") or "")
    return ""
