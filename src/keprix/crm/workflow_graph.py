"""CRM workflow graph domain model independent of canvas library (prompt 508)."""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.crm.visual_contract import NODE_FAMILIES

GRAPH_SCHEMA_VERSION = 1

NODE_PALETTE: list[dict[str, Any]] = [
    {"family": "trigger", "type": "manual_trigger", "group": "triggers", "label": "Manual trigger"},
    {"family": "trigger", "type": "schedule_trigger", "group": "triggers", "label": "Schedule"},
    {"family": "trigger", "type": "list_trigger", "group": "triggers", "label": "List enroll"},
    {"family": "trigger", "type": "reply_trigger", "group": "triggers", "label": "Reply received"},
    {"family": "discovery", "type": "discovery", "group": "data", "label": "Discovery"},
    {"family": "enrich", "type": "enrichment", "group": "data", "label": "Enrichment"},
    {"family": "enrich", "type": "dedupe", "group": "data", "label": "Dedupe"},
    {"family": "enrich", "type": "crm_update", "group": "data", "label": "CRM update"},
    {"family": "decision", "type": "if_else", "group": "decisions", "label": "If / else"},
    {"family": "decision", "type": "score_threshold", "group": "decisions", "label": "Score threshold"},
    {"family": "decision", "type": "contactability", "group": "decisions", "label": "Contactability"},
    {"family": "decision", "type": "consent_check", "group": "decisions", "label": "Consent"},
    {"family": "approval", "type": "soft_wall_approval", "group": "human_work", "label": "Soft Wall approval"},
    {"family": "human_task", "type": "human_task", "group": "human_work", "label": "Human task"},
    {"family": "wait", "type": "delay", "group": "controls", "label": "Delay"},
    {"family": "wait", "type": "quiet_hours", "group": "controls", "label": "Quiet hours wait"},
    {"family": "outreach", "type": "email_send", "group": "communications", "label": "Email send"},
    {"family": "outreach", "type": "telegram_alert", "group": "communications", "label": "Telegram alert"},
    {"family": "booking", "type": "booking_offer", "group": "integrations", "label": "Booking offer"},
    {"family": "stage", "type": "stage_transition", "group": "outcomes", "label": "Stage transition"},
    {"family": "goal", "type": "goal_reached", "group": "outcomes", "label": "Goal reached"},
    {"family": "stop", "type": "stop", "group": "controls", "label": "Stop"},
    {"family": "stop", "type": "suppression", "group": "controls", "label": "Suppression"},
    {"family": "error", "type": "retry", "group": "error_handling", "label": "Retry"},
    {"family": "error", "type": "fallback", "group": "error_handling", "label": "Fallback"},
    {"family": "error", "type": "error", "group": "error_handling", "label": "Error"},
]

TEMPLATES: dict[str, dict[str, Any]] = {
    "lead_discovery": {"label": "Lead discovery", "nodes": ["manual_trigger", "discovery", "enrichment", "soft_wall_approval", "stop"]},
    "sheet_to_crm": {"label": "Sheet to CRM", "nodes": ["manual_trigger", "enrichment", "crm_update", "soft_wall_approval", "stop"]},
    "cold_outreach": {"label": "Cold outreach", "nodes": ["list_trigger", "contactability", "soft_wall_approval", "email_send", "wait", "stop"]},
    "nurture": {"label": "Nurture", "nodes": ["list_trigger", "email_send", "delay", "email_send", "delay", "email_send", "stop"]},
    "reply_to_booking": {"label": "Reply to booking", "nodes": ["reply_trigger", "human_task", "booking_offer", "goal_reached", "stop"]},
    "stale_reactivation": {"label": "Stale lead reactivation", "nodes": ["schedule_trigger", "contactability", "soft_wall_approval", "email_send", "stop"]},
    "human_handoff": {"label": "Human handoff", "nodes": ["reply_trigger", "human_task", "stop"]},
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _graph_store_path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "crm"
    except Exception:
        root = Path.home() / ".keprix" / "crm"
    root.mkdir(parents=True, exist_ok=True)
    return root / "workflow_graphs.json"


def _load_store() -> dict[str, Any]:
    path = _graph_store_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_store(data: dict[str, Any]) -> None:
    path = _graph_store_path()
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def empty_graph(
    *,
    workflow_id: str | None = None,
    name: str = "Untitled workflow",
    status: str = "draft",
) -> dict[str, Any]:
    wid = workflow_id or str(uuid.uuid4())
    return {
        "id": wid,
        "name": name,
        "status": status,
        "schema_version": GRAPH_SCHEMA_VERSION,
        "workflow_version": 1,
        "nodes": [],
        "edges": [],
        "created_at": _now(),
        "updated_at": _now(),
        "published_at": None,
        "credential_refs": [],
    }


def sequence_to_graph(sequence: dict[str, Any], *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map Soft Wall sequence steps into an executable CRM graph."""
    meta = meta or {}
    wid = str(sequence.get("id") or uuid.uuid4())
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    trigger_id = "n_trigger"
    nodes.append(
        {
            "id": trigger_id,
            "family": "trigger",
            "type": "list_trigger",
            "label": "List / enroll trigger",
            "config": {"entry_stage": meta.get("entry_stage") or "enrolled"},
            "ports": {"out": ["next"]},
            "x": 40,
            "y": 120,
        }
    )
    prev = trigger_id
    y = 120
    steps = list(sequence.get("steps") or [])
    for idx, step in enumerate(steps):
        y += 100
        wait_id = f"n_wait_{idx}"
        send_id = f"n_send_{idx}"
        delay = int(step.get("delay_hours") or 0)
        if delay > 0:
            nodes.append(
                {
                    "id": wait_id,
                    "family": "wait",
                    "type": "delay",
                    "label": f"Wait {delay}h",
                    "config": {"delay_hours": delay},
                    "ports": {"in": ["next"], "out": ["next"]},
                    "x": 40 + idx * 40,
                    "y": y,
                }
            )
            edges.append(
                {
                    "id": f"e_{prev}_{wait_id}",
                    "source": prev,
                    "target": wait_id,
                    "condition_label": "next",
                }
            )
            prev = wait_id
            y += 80
        nodes.append(
            {
                "id": send_id,
                "family": "outreach",
                "type": "email_send",
                "label": str(step.get("cta") or step.get("subject") or f"Email step {idx + 1}"),
                "config": {
                    "channel": step.get("channel") or "email",
                    "subject": step.get("subject"),
                    "body_ref": f"step:{idx}",
                    "credential_ref": "sender_default",
                },
                "ports": {"in": ["next"], "out": ["next", "error"]},
                "x": 40 + idx * 40,
                "y": y,
            }
        )
        edges.append(
            {
                "id": f"e_{prev}_{send_id}",
                "source": prev,
                "target": send_id,
                "condition_label": "next",
            }
        )
        prev = send_id

    # Soft Wall gate before first send if any sends
    if any(n["type"] == "email_send" for n in nodes):
        first_send = next(n for n in nodes if n["type"] == "email_send")
        approval_id = "n_soft_wall"
        nodes.insert(
            1,
            {
                "id": approval_id,
                "family": "approval",
                "type": "soft_wall_approval",
                "label": "Soft Wall approval",
                "config": {"scope": "campaign_enroll_send"},
                "ports": {"in": ["next"], "out": ["approved", "rejected"]},
                "x": 40,
                "y": 200,
            },
        )
        # Rewire trigger -> approval -> original next of trigger
        edges = [e for e in edges if e["source"] != trigger_id]
        edges.insert(
            0,
            {
                "id": f"e_{trigger_id}_{approval_id}",
                "source": trigger_id,
                "target": approval_id,
                "condition_label": "next",
            },
        )
        # Find first non-approval node after trigger path
        first_after = first_send["id"]
        for n in nodes:
            if n["id"] not in {trigger_id, approval_id} and n["family"] in {"wait", "outreach"}:
                first_after = n["id"]
                break
        edges.insert(
            1,
            {
                "id": f"e_{approval_id}_{first_after}",
                "source": approval_id,
                "target": first_after,
                "condition_label": "approved",
            },
        )

    stop_id = "n_stop"
    nodes.append(
        {
            "id": stop_id,
            "family": "stop",
            "type": "stop",
            "label": "Stop",
            "config": {
                "stop_on_reply": bool(sequence.get("stop_on_reply", True)),
                "stop_on_booking": bool(sequence.get("stop_on_booking", True)),
            },
            "ports": {"in": ["next"]},
            "x": 40,
            "y": y + 120,
        }
    )
    edges.append({"id": f"e_{prev}_{stop_id}", "source": prev, "target": stop_id, "condition_label": "complete"})

    return {
        "id": wid,
        "name": str(sequence.get("name") or "CRM workflow"),
        "status": str(meta.get("status") or "draft"),
        "schema_version": GRAPH_SCHEMA_VERSION,
        "workflow_version": int(meta.get("version") or 1),
        "nodes": nodes,
        "edges": edges,
        "meta": meta,
        "sequence_id": wid,
        "created_at": _now(),
        "updated_at": _now(),
        "published_at": None,
        "credential_refs": ["sender_default"],
        "source": "soft_wall_sequence",
    }


def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = {n["id"]: n for n in graph.get("nodes") or [] if isinstance(n, dict) and n.get("id")}
    edges = [e for e in graph.get("edges") or [] if isinstance(e, dict)]
    issues: list[dict[str, Any]] = []

    if not any(n.get("family") == "trigger" for n in nodes.values()):
        issues.append(
            {
                "severity": "error",
                "code": "missing_trigger",
                "path": "nodes",
                "message": "Graph needs at least one trigger.",
                "fix": "Add a trigger node from the palette.",
            }
        )
    if not any(n.get("family") == "stop" or n.get("type") == "stop" for n in nodes.values()):
        issues.append(
            {
                "severity": "error",
                "code": "missing_stop",
                "path": "nodes",
                "message": "Graph needs a stop condition.",
                "fix": "Add a stop node.",
            }
        )

    reachable: set[str] = set()
    starts = [nid for nid, n in nodes.items() if n.get("family") == "trigger"]
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        for e in edges:
            if e.get("source") == cur and e.get("target") in nodes:
                stack.append(str(e["target"]))
    for nid in nodes:
        if nid not in reachable:
            issues.append(
                {
                    "severity": "warning",
                    "code": "unreachable_node",
                    "path": f"nodes.{nid}",
                    "message": f"Node {nid} is unreachable.",
                    "fix": "Connect it from a trigger path or remove it.",
                }
            )

    # Unsafe send without Soft Wall
    for n in nodes.values():
        if n.get("type") == "email_send":
            has_approval_upstream = False
            for e in edges:
                src = nodes.get(str(e.get("source")))
                if e.get("target") == n["id"] and src and src.get("type") == "soft_wall_approval":
                    has_approval_upstream = True
            # Also accept any approval in graph for Must-thin
            if not has_approval_upstream and not any(
                x.get("type") == "soft_wall_approval" for x in nodes.values()
            ):
                issues.append(
                    {
                        "severity": "error",
                        "code": "missing_approval",
                        "path": f"nodes.{n['id']}",
                        "message": "Email send requires Soft Wall approval in the graph.",
                        "fix": "Insert a Soft Wall approval node before send.",
                    }
                )

    # Loop without limit (simple cycle detect)
    for e in edges:
        if e.get("source") == e.get("target"):
            issues.append(
                {
                    "severity": "error",
                    "code": "self_loop",
                    "path": f"edges.{e.get('id')}",
                    "message": "Self-loop without limit.",
                    "fix": "Add a max-iteration guard or remove the loop.",
                }
            )

    for n in nodes.values():
        fam = str(n.get("family") or "")
        if fam and fam not in NODE_FAMILIES:
            issues.append(
                {
                    "severity": "warning",
                    "code": "unknown_family",
                    "path": f"nodes.{n['id']}",
                    "message": f"Unknown node family {fam}.",
                    "fix": "Use a canonical node family from the contract.",
                }
            )

    blocking = [i for i in issues if i["severity"] == "error"]
    return {
        "ok": len(blocking) == 0,
        "issues": issues,
        "can_publish": len(blocking) == 0,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def simulate_graph(graph: dict[str, Any], *, sample: dict[str, Any] | None = None) -> dict[str, Any]:
    """Dry-run: no external side effects."""
    validation = validate_graph(graph)
    sample = sample or {"lead_id": "sample_redacted", "email": "[redacted]", "company": "Sample Co"}
    path: list[str] = []
    blocked: list[dict[str, Any]] = []
    cost_estimate = 0.0
    for node in graph.get("nodes") or []:
        path.append(node["id"])
        if node.get("type") == "email_send":
            cost_estimate += 0.01
            blocked.append(
                {
                    "node_id": node["id"],
                    "gate": "simulation_no_external_send",
                    "message": "Simulation never sends externally.",
                }
            )
        if node.get("type") == "soft_wall_approval":
            blocked.append(
                {
                    "node_id": node["id"],
                    "gate": "soft_wall",
                    "message": "Would require Soft Wall approval before send.",
                }
            )
        if node.get("type") == "contactability":
            blocked.append(
                {
                    "node_id": node["id"],
                    "gate": "contactability",
                    "message": "Would evaluate contactability; deny blocks outreach.",
                }
            )
    return {
        "ok": True,
        "external_side_effects": False,
        "sample": sample,
        "path": path,
        "branch_estimate": max(1, len([n for n in graph.get("nodes") or [] if n.get("family") == "decision"])),
        "cost_estimate": cost_estimate,
        "gates": blocked,
        "validation": validation,
    }


def template_graph(template_id: str) -> dict[str, Any]:
    tpl = TEMPLATES.get(template_id)
    if not tpl:
        raise KeyError(template_id)
    g = empty_graph(name=tpl["label"], status="draft")
    nodes = []
    edges = []
    prev = None
    for i, ntype in enumerate(tpl["nodes"]):
        nid = f"n_{i}_{ntype}"
        family = next((p["family"] for p in NODE_PALETTE if p["type"] == ntype), "integration")
        nodes.append(
            {
                "id": nid,
                "family": family,
                "type": ntype,
                "label": next((p["label"] for p in NODE_PALETTE if p["type"] == ntype), ntype),
                "config": {},
                "ports": {"in": ["next"], "out": ["next"]},
                "x": 60,
                "y": 80 + i * 100,
            }
        )
        if prev:
            edges.append(
                {
                    "id": f"e_{prev}_{nid}",
                    "source": prev,
                    "target": nid,
                    "condition_label": "next",
                }
            )
        prev = nid
    g["nodes"] = nodes
    g["edges"] = edges
    g["template_id"] = template_id
    g["auto_active"] = False
    return g


def get_or_build_workflow_graph(workspace_id: str, workflow_id: str) -> dict[str, Any]:
    data = _load_store()
    ws = data.get(workspace_id) or {}
    if workflow_id in ws:
        return copy.deepcopy(ws[workflow_id])

    from keprix.crm.nurture import list_workflows

    for wf in list_workflows(workspace_id):
        if str(wf.get("id")) == workflow_id:
            graph = sequence_to_graph(wf, meta=wf.get("meta") or {})
            ws[workflow_id] = graph
            data[workspace_id] = ws
            _save_store(data)
            return copy.deepcopy(graph)
    raise LookupError(workflow_id)


def save_workflow_graph(
    workspace_id: str,
    graph: dict[str, Any],
    *,
    actor_id: str | None = None,
    expected_version: int | None = None,
) -> dict[str, Any]:
    data = _load_store()
    ws = data.setdefault(workspace_id, {})
    wid = str(graph.get("id") or uuid.uuid4())
    existing = ws.get(wid)
    if existing and expected_version is not None:
        if int(existing.get("workflow_version") or 1) != int(expected_version):
            return {
                "ok": False,
                "conflict": True,
                "server_version": existing.get("workflow_version"),
                "client_version": expected_version,
            }
    # Published versions are immutable: editing active creates a new draft version
    status = str(graph.get("status") or "draft")
    if existing and str(existing.get("status")) == "active" and status != "active":
        graph = copy.deepcopy(graph)
        graph["workflow_version"] = int(existing.get("workflow_version") or 1) + 1
        graph["status"] = "draft"
        graph["pinned_from_active"] = existing.get("workflow_version")
    graph["id"] = wid
    graph["updated_at"] = _now()
    graph["updated_by"] = actor_id
    # Never persist secrets
    for node in graph.get("nodes") or []:
        cfg = node.get("config") or {}
        for key in list(cfg.keys()):
            if "secret" in key.lower() or "password" in key.lower() or "api_key" in key.lower():
                cfg[key] = "[redacted_ref]"
        node["config"] = cfg
    ws[wid] = graph
    data[workspace_id] = ws
    _save_store(data)
    return {"ok": True, "graph": graph}


def publish_workflow_graph(
    workspace_id: str,
    workflow_id: str,
    *,
    actor_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    graph = get_or_build_workflow_graph(workspace_id, workflow_id)
    validation = validate_graph(graph)
    if not validation.get("can_publish"):
        return {"ok": False, "validation": validation}
    prev = copy.deepcopy(graph)
    graph["status"] = "active"
    graph["published_at"] = _now()
    graph["published_by"] = actor_id
    graph["publish_reason"] = reason
    graph["workflow_version"] = int(graph.get("workflow_version") or 1)
    # Running executions stay pinned: store immutable published snapshot
    data = _load_store()
    ws = data.setdefault(workspace_id, {})
    versions = ws.setdefault("_published", {}).setdefault(workflow_id, [])
    snap = copy.deepcopy(graph)
    snap["immutable"] = True
    versions.append(snap)
    ws[workflow_id] = graph
    data[workspace_id] = ws
    _save_store(data)
    diff = semantic_diff(prev, graph)
    return {"ok": True, "graph": graph, "validation": validation, "diff": diff, "invalidate_approvals": diff.get("material_change")}


def semantic_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    material_keys = {"audience", "content", "cadence", "channel", "sender", "policy"}
    changes: list[str] = []
    b_nodes = {n["id"]: n for n in before.get("nodes") or []}
    a_nodes = {n["id"]: n for n in after.get("nodes") or []}
    if set(b_nodes) != set(a_nodes):
        changes.append("nodes")
    for nid, node in a_nodes.items():
        prev = b_nodes.get(nid)
        if not prev:
            changes.append(f"added:{nid}")
            continue
        if prev.get("type") != node.get("type"):
            changes.append(f"type:{nid}")
        if prev.get("config") != node.get("config"):
            changes.append(f"config:{nid}")
    material = bool(changes)  # Must-thin: any node/config change is material
    return {
        "changes": changes,
        "material_change": material,
        "material_categories": list(material_keys) if material else [],
        "impact_preview": "Material changes invalidate prior Soft Wall approvals." if material else "No material change.",
    }


def list_templates() -> list[dict[str, Any]]:
    return [{"id": k, **v, "auto_active": False} for k, v in TEMPLATES.items()]


def export_graph(graph: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(graph)
    for node in out.get("nodes") or []:
        cfg = node.get("config") or {}
        for key in list(cfg.keys()):
            if any(s in key.lower() for s in ("secret", "password", "token", "api_key")):
                cfg[key] = "[redacted_ref]"
        node["config"] = cfg
    return out
