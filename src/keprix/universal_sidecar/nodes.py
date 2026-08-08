"""Universal capability nodes and playbook validation (KUS-05)."""

from __future__ import annotations

from typing import Any

from keprix.universal_sidecar.connector import ConnectorError, get_connector
from keprix.universal_sidecar.manifest.schema import DANGEROUS_NODE_PREFIXES, SAFE_BUILTIN_NODES
from keprix.universal_sidecar.registry import get_project_registry

NODE_META: dict[str, dict[str, Any]] = {
    "prompt.transform": {"risk": "read", "grants": ("invoke:prompt.transform",)},
    "classify": {"risk": "read", "grants": ("invoke:classify",)},
    "summarise": {"risk": "read", "grants": ("invoke:summarise",)},
    "extract": {"risk": "read", "grants": ("invoke:extract",)},
    "compare": {"risk": "read", "grants": ("invoke:compare",)},
    "validate": {"risk": "read", "grants": ("invoke:validate",)},
    "memory.retrieve": {"risk": "read", "grants": ("memory:ephemeral/read",)},
    "project.read": {"risk": "read", "grants": ("discover",)},
    "proposal.prepare": {"risk": "propose", "grants": ("invoke:proposal.prepare",)},
    "wait": {"risk": "read", "grants": ("invoke:wait",)},
    "decision": {"risk": "read", "grants": ("invoke:decision",)},
    "approval.request": {"risk": "propose", "grants": ("approvals",)},
    "event.emit": {"risk": "read", "grants": ("events",)},
    "finish": {"risk": "read", "grants": ("discover",)},
}


class NodeError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def catalog_for_project(project_key: str) -> list[dict[str, Any]]:
    row = get_project_registry().require(project_key)
    requested = {c.get("node") for c in (row["manifest"].get("capabilities") or [])}
    out = []
    for key in sorted(SAFE_BUILTIN_NODES):
        meta = NODE_META.get(key, {"risk": "read", "grants": (f"invoke:{key}",)})
        out.append(
            {
                "key": key,
                "version": "1.0.0",
                "risk": meta["risk"],
                "status": "live" if key in requested or not requested else "available",
                "required_grants": list(meta["grants"]),
                "sandbox": False,
            }
        )
    return out


async def invoke_safe_node(
    *,
    project_key: str,
    node_key: str,
    input_payload: dict[str, Any],
    grants: frozenset[str],
    tenant_id: str = "",
    actor_id: str = "",
    correlation_id: str = "",
    simulate: bool = False,
) -> dict[str, Any]:
    registry = get_project_registry()
    row = registry.require(project_key)
    if not row.get("enabled") or registry.is_killed(project_key):
        raise NodeError("pack_disabled", "project disabled or killed", 503)
    if registry.is_killed(project_key, node=node_key):
        raise NodeError("denied", "node kill switch")
    if any(node_key.startswith(p) for p in DANGEROUS_NODE_PREFIXES):
        raise NodeError("denied", "dangerous node unavailable in universal quickstart")
    if node_key not in SAFE_BUILTIN_NODES:
        raise NodeError("unknown_node", f"unknown node {node_key}", 404)

    meta = NODE_META.get(node_key, {})
    required = meta.get("grants") or (f"invoke:{node_key}",)
    if not any(g in grants or "*" in grants for g in required) and f"invoke:{node_key}" not in grants:
        # allow discover for finish/project.read defaults
        if not (set(required) & set(grants)) and "*" not in grants:
            raise NodeError("denied", "missing grant")

    if not registry.consume_budget(project_key, kind="requests"):
        raise NodeError("budget_exceeded", "budget exceeded", 429)

    # Policy recheck before side effects
    if meta.get("risk") in {"mutate", "outbound", "destructive"} and not simulate:
        raise NodeError("denied", "side-effect risk requires installed capability")

    payload = dict(input_payload or {})
    # Untrusted data cannot alter policy
    payload.pop("grants", None)
    payload.pop("__policy__", None)

    if simulate:
        return {
            "node": node_key,
            "simulate": True,
            "external_side_effects": 0,
            "forecast": {"path": [node_key], "cost_units": 1, "gates": []},
            "output": {"ok": True, "echo": _safe_echo(payload)},
        }

    if node_key == "project.read":
        op = str(payload.get("operation") or "")
        params = dict(payload.get("params") or {})
        try:
            result = get_connector(project_key).read(op, params)
        except ConnectorError as exc:
            raise NodeError(exc.code, exc.message, 502) from exc
        return {"node": node_key, "output": result, "correlation_id": correlation_id}

    if node_key == "summarise":
        text = str(payload.get("text") or "")
        summary = text.strip()[:280] + ("..." if len(text.strip()) > 280 else "")
        return {"node": node_key, "output": {"summary": summary or "(empty)"}, "correlation_id": correlation_id}

    if node_key == "classify":
        text = str(payload.get("text") or "").lower()
        label = "urgent" if "urgent" in text or "asap" in text else "normal"
        return {"node": node_key, "output": {"label": label}, "correlation_id": correlation_id}

    if node_key == "extract":
        return {
            "node": node_key,
            "output": {"fields": payload.get("fields") or {}, "source_len": len(str(payload.get("text") or ""))},
            "correlation_id": correlation_id,
        }

    if node_key == "validate":
        schema_ok = "text" in payload or "data" in payload
        return {"node": node_key, "output": {"valid": schema_ok}, "correlation_id": correlation_id}

    if node_key == "compare":
        return {
            "node": node_key,
            "output": {"equal": payload.get("a") == payload.get("b")},
            "correlation_id": correlation_id,
        }

    if node_key == "prompt.transform":
        return {
            "node": node_key,
            "output": {"text": str(payload.get("text") or "").strip()},
            "correlation_id": correlation_id,
        }

    if node_key == "proposal.prepare":
        import hashlib
        import json

        body = {"action": payload.get("action"), "input": payload.get("input") or {}}
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        return {
            "node": node_key,
            "output": {"proposal": body, "input_hash": digest, "requires_approval": True},
            "correlation_id": correlation_id,
        }

    if node_key == "approval.request":
        from keprix.universal_sidecar.jobs import get_approval_store

        approval = get_approval_store().create(
            project_key=project_key,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=str(payload.get("action") or "propose"),
            input_hash=str(payload.get("input_hash") or ""),
            payload=payload,
        )
        return {"node": node_key, "output": {"approval": approval}, "correlation_id": correlation_id}

    if node_key == "memory.retrieve":
        from keprix.universal_sidecar.memory import get_memory_service

        hits = get_memory_service().search(
            project_key=project_key,
            tenant_id=tenant_id,
            query=str(payload.get("query") or ""),
            namespace=str(payload.get("namespace") or "ephemeral"),
        )
        return {"node": node_key, "output": {"hits": hits}, "correlation_id": correlation_id}

    if node_key == "event.emit":
        from keprix.universal_sidecar.events import get_event_service

        ev = get_event_service().emit_outbound(
            project_key=project_key,
            event_type=str(payload.get("type") or "keprix.node.completed"),
            data=payload.get("data") or {},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        return {"node": node_key, "output": {"event": ev}, "correlation_id": correlation_id}

    if node_key in {"wait", "decision", "finish"}:
        return {"node": node_key, "output": {"ok": True, "input": _safe_echo(payload)}, "correlation_id": correlation_id}

    raise NodeError("unknown_node", f"unhandled node {node_key}", 404)


def _safe_echo(payload: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in list(payload.items())[:20]:
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v if not isinstance(v, str) else v[:500]
        else:
            out[k] = type(v).__name__
    return out


def validate_playbook_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Validate schema compatibility, cycles, bounded loops, approvals."""
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    issues: list[str] = []
    ids = {n.get("id") for n in nodes}
    for e in edges:
        if e.get("from") not in ids or e.get("to") not in ids:
            issues.append(f"edge references missing node: {e}")
    # Cycle detection (simple DFS)
    adj: dict[str, list[str]] = {str(n.get("id")): [] for n in nodes}
    for e in edges:
        adj[str(e.get("from"))].append(str(e.get("to")))
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(n: str) -> None:
        if n in visiting:
            issues.append(f"cycle involving {n}")
            return
        if n in visited:
            return
        visiting.add(n)
        for nxt in adj.get(n, []):
            dfs(nxt)
        visiting.discard(n)
        visited.add(n)

    for n in list(adj):
        dfs(n)

    for n in nodes:
        key = str(n.get("node") or "")
        if any(key.startswith(p) for p in DANGEROUS_NODE_PREFIXES):
            issues.append(f"dangerous node in playbook: {key}")
        if key and key not in SAFE_BUILTIN_NODES:
            issues.append(f"unknown node in playbook: {key}")
        if n.get("side_effect") and not n.get("approval"):
            issues.append(f"side-effect node {n.get('id')} missing approval gate")

    return {"ok": len(issues) == 0, "issues": issues, "node_count": len(nodes), "edge_count": len(edges)}
