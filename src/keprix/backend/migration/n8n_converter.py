"""Best-effort n8n workflow JSON to Keprix playbook YAML converter (Prompt 207)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

TRIGGER_TYPES = {
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.scheduleTrigger",
}

SUPPORTED_TYPES = {
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.code",
    "n8n-nodes-base.if",
    "n8n-nodes-base.set",
    *TRIGGER_TYPES,
}


@dataclass
class N8nConversionResult:
    playbook_id: str
    name: str
    yaml_text: str
    mapped_nodes: list[str] = field(default_factory=list)
    skipped_nodes: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def report_dict(self) -> dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "mapped_nodes": list(self.mapped_nodes),
            "skipped_nodes": list(self.skipped_nodes),
            "warnings": list(self.warnings),
        }


def load_n8n_export(path: Path) -> dict[str, Any]:
    """Load an n8n workflow export JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        if not raw:
            raise ValueError("Workflow export list is empty")
        raw = raw[0]
    if not isinstance(raw, dict):
        raise ValueError("Workflow export must be a JSON object")
    if isinstance(raw.get("data"), dict) and "nodes" in raw["data"]:
        raw = raw["data"]
    if "nodes" not in raw:
        raise ValueError("Workflow export missing 'nodes' array")
    return raw


def convert_n8n_workflow(payload: dict[str, Any], *, playbook_id: str | None = None) -> N8nConversionResult:
    """Convert an n8n workflow payload to Keprix playbook YAML."""
    nodes = [node for node in payload.get("nodes") or [] if isinstance(node, dict)]
    connections = payload.get("connections") if isinstance(payload.get("connections"), dict) else {}

    workflow_name = str(payload.get("name") or "Imported n8n workflow").strip()
    slug = playbook_id or _slugify_playbook_id(workflow_name)

    used_ids: set[str] = set()
    name_to_step_id: dict[str, str] = {}
    steps: list[dict[str, Any]] = []
    mapped_nodes: list[str] = []
    skipped_nodes: list[dict[str, str]] = []
    warnings: list[str] = []
    metadata_notes: list[str] = []

    for node in nodes:
        node_name = str(node.get("name") or "node").strip()
        node_type = str(node.get("type") or "").strip()
        if node.get("disabled"):
            skipped_nodes.append(
                {"name": node_name, "type": node_type, "reason": "disabled_node"}
            )
            continue

        if node_type in TRIGGER_TYPES:
            mapped_nodes.append(node_name)
            metadata_notes.extend(_trigger_notes(node_type, node_name, node))
            continue

        if node_type not in SUPPORTED_TYPES:
            skipped_nodes.append(
                {"name": node_name, "type": node_type, "reason": "unsupported_node_type"}
            )
            continue

        step_id = _unique_step_id(node_name, used_ids)
        name_to_step_id[node_name] = step_id
        parameters = node.get("parameters") if isinstance(node.get("parameters"), dict) else {}

        if node_type == "n8n-nodes-base.httpRequest":
            step = _map_http_step(step_id, parameters)
        elif node_type == "n8n-nodes-base.code":
            step = _map_code_step(step_id, parameters)
        elif node_type == "n8n-nodes-base.if":
            step, warn = _map_if_step(step_id, parameters, connections, node_name)
            if warn:
                warnings.append(warn)
        elif node_type == "n8n-nodes-base.set":
            step = _map_set_step(step_id, node_name, parameters)
        elif node_type == "n8n-nodes-base.webhook":
            step = _map_webhook_stub(step_id, parameters)
        else:
            skipped_nodes.append(
                {"name": node_name, "type": node_type, "reason": "unsupported_node_type"}
            )
            continue

        steps.append(step)
        mapped_nodes.append(node_name)

    edges = _build_edges(connections, name_to_step_id, skipped_nodes, warnings)
    entry = _infer_entry_step(steps, edges)

    description_parts = ["Imported from n8n (best-effort conversion)."]
    if metadata_notes:
        description_parts.extend(metadata_notes)

    playbook: dict[str, Any] = {
        "id": slug,
        "name": workflow_name,
        "description": " ".join(description_parts),
        "steps": steps,
        "edges": edges,
    }
    if entry:
        playbook["entry"] = entry

    header = _review_header(skipped_nodes, warnings)
    yaml_body = yaml.safe_dump(
        playbook,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    yaml_text = f"{header}\n{yaml_body}".rstrip() + "\n"

    return N8nConversionResult(
        playbook_id=slug,
        name=workflow_name,
        yaml_text=yaml_text,
        mapped_nodes=mapped_nodes,
        skipped_nodes=skipped_nodes,
        warnings=warnings,
    )


def _slugify_playbook_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "imported-n8n-workflow")[:48]


def _unique_step_id(name: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "step"
    base = base[:48]
    candidate = base
    suffix = 2
    while candidate in used:
        tail = f"-{suffix}"
        candidate = f"{base[: max(1, 48 - len(tail))]}{tail}"
        suffix += 1
    used.add(candidate)
    return candidate


def _normalize_n8n_value(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("={{") and stripped.endswith("}}"):
            inner = stripped[3:-2].strip()
            if inner.startswith("$json"):
                return f"# TODO: replace with {{{{ steps.<prev>.output{inner[5:]} }}}}"
            return f"{{{{ n8n_expr:{inner} }}}}"
        return value
    if isinstance(value, dict):
        return {str(k): _normalize_n8n_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_n8n_value(item) for item in value]
    return value


def _parameter_pairs(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    rows = raw.get("parameters")
    if not isinstance(rows, list):
        return {}
    result: dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("name") or "").strip()
        if not key:
            continue
        result[key] = _normalize_n8n_value(row.get("value"))
    return result


def _map_http_step(step_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    step: dict[str, Any] = {
        "id": step_id,
        "type": "http",
        "url": _normalize_n8n_value(str(parameters.get("url") or "")),
        "method": str(parameters.get("method") or parameters.get("requestMethod") or "GET").upper(),
    }
    query = _parameter_pairs(parameters.get("queryParameters"))
    if query:
        step["query"] = query
    body = _parameter_pairs(parameters.get("bodyParameters"))
    if body:
        step["body"] = body
    json_body = parameters.get("jsonBody")
    if json_body:
        step["body"] = _normalize_n8n_value(json_body)
    return step


def _map_code_step(step_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    js_code = parameters.get("jsCode")
    python_code = parameters.get("pythonCode")
    if python_code:
        source = str(python_code)
        language = "python"
    else:
        source = str(js_code or "")
        language = "javascript"
    return {
        "id": step_id,
        "type": "code",
        "language": language,
        "source": source,
    }


def _map_if_step(
    step_id: str,
    parameters: dict[str, Any],
    connections: dict[str, Any],
    node_name: str,
) -> tuple[dict[str, Any], str | None]:
    warning: str | None = None
    conditions_block = parameters.get("conditions")
    expression = "true"
    if isinstance(conditions_block, dict):
        rows = conditions_block.get("conditions")
        if isinstance(rows, list) and rows:
            first = rows[0] if isinstance(rows[0], dict) else {}
            left = _normalize_n8n_value(str(first.get("leftValue") or ""))
            right = _normalize_n8n_value(first.get("rightValue"))
            operator = first.get("operator") if isinstance(first.get("operator"), dict) else {}
            operation = str(operator.get("operation") or "equals")
            expression = f"{left} {operation} {right}"
            if "{{ n8n_expr:" in expression:
                warning = (
                    f"If node '{node_name}' uses n8n expressions; review expression manually."
                )
                expression = f"# TODO: translate n8n if expression\n{expression}"

    branch_targets = _if_branch_targets(connections, node_name)
    step: dict[str, Any] = {
        "id": step_id,
        "type": "condition",
        "expression": expression,
    }
    if branch_targets[0]:
        step["on_true"] = branch_targets[0]
    if branch_targets[1]:
        step["on_false"] = branch_targets[1]
    return step, warning


def _if_branch_targets(connections: dict[str, Any], node_name: str) -> tuple[str | None, str | None]:
    block = connections.get(node_name)
    if not isinstance(block, dict):
        return None, None
    mains = block.get("main")
    if not isinstance(mains, list):
        return None, None
    targets: list[str | None] = []
    for branch in mains[:2]:
        target_name = None
        if isinstance(branch, list) and branch:
            first = branch[0]
            if isinstance(first, dict):
                target_name = str(first.get("node") or "").strip() or None
        targets.append(target_name)
    while len(targets) < 2:
        targets.append(None)
    return targets[0], targets[1]


def _map_set_step(step_id: str, node_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    assignments = parameters.get("assignments")
    lines = ["# Set fields converted from n8n Edit Fields node", "state = dict(locals().get('state') or {})"]
    if isinstance(assignments, dict):
        rows = assignments.get("assignments")
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                key = str(row.get("name") or "field")
                value = _normalize_n8n_value(row.get("value"))
                lines.append(f"state[{key!r}] = {value!r}")
    lines.append("result = state")
    return {
        "id": step_id,
        "type": "code",
        "language": "python",
        "source": "\n".join(lines),
        "comment": f"Converted from n8n set node '{node_name}'",
    }


def _map_webhook_stub(step_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    path = _normalize_n8n_value(str(parameters.get("path") or "/webhook/imported"))
    return {
        "id": step_id,
        "type": "http",
        "url": f"https://example.com{path}",
        "method": "POST",
        "comment": "Replace with a Keprix webhook trigger route",
    }


def _trigger_notes(node_type: str, node_name: str, node: dict[str, Any]) -> list[str]:
    if node_type == "n8n-nodes-base.manualTrigger":
        return [f"Manual trigger '{node_name}' mapped to metadata only."]
    if node_type == "n8n-nodes-base.scheduleTrigger":
        return ["Schedule via Keprix cron or agent-apps (converted from n8n schedule trigger)."]
    if node_type == "n8n-nodes-base.webhook":
        path = str((node.get("parameters") or {}).get("path") or "")
        note = "Replace n8n webhook with a Keprix webhook trigger route."
        if path:
            note = f"{note} Original path: {path}"
        return [note]
    return []


def _build_edges(
    connections: dict[str, Any],
    name_to_step_id: dict[str, str],
    skipped_nodes: list[dict[str, str]],
    warnings: list[str],
) -> list[dict[str, str]]:
    skipped_names = {row["name"] for row in skipped_nodes}
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for source_name, block in connections.items():
        if source_name in skipped_names:
            continue
        source_id = name_to_step_id.get(source_name)
        if source_id is None:
            continue
        if not isinstance(block, dict):
            continue
        mains = block.get("main")
        if not isinstance(mains, list):
            continue
        for branch in mains:
            if not isinstance(branch, list):
                continue
            for link in branch:
                if not isinstance(link, dict):
                    continue
                target_name = str(link.get("node") or "").strip()
                if not target_name or target_name in skipped_names:
                    if target_name in skipped_names:
                        warnings.append(
                            f"Skipped edge to disabled/unsupported node '{target_name}'."
                        )
                    continue
                target_id = name_to_step_id.get(target_name)
                if target_id is None:
                    continue
                key = (source_id, target_id)
                if key in seen:
                    continue
                seen.add(key)
                edges.append({"from": source_id, "to": target_id})
    return edges


def _infer_entry_step(steps: list[dict[str, Any]], edges: list[dict[str, str]]) -> str | None:
    if not steps:
        return None
    targets = {edge["to"] for edge in edges}
    step_ids = [str(step.get("id") or "") for step in steps if step.get("id")]
    roots = [step_id for step_id in step_ids if step_id not in targets]
    if len(roots) == 1:
        return roots[0]
    if len(step_ids) == 1:
        return step_ids[0]
    return roots[0] if roots else None


def _review_header(skipped_nodes: list[dict[str, str]], warnings: list[str]) -> str:
    lines = [
        "# Imported from n8n (best-effort conversion)",
        "# Review skipped nodes and expression placeholders before running.",
    ]
    if skipped_nodes:
        lines.append("# Skipped nodes:")
        for row in skipped_nodes:
            lines.append(f"# - {row['name']} ({row['type']}): {row['reason']}")
    if warnings:
        lines.append("# Warnings:")
        for warning in warnings:
            lines.append(f"# - {warning}")
    return "\n".join(lines)
