"""Node inspector contract for design, simulation, live, and replay (prompt 510)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.crm.workflow_graph import validate_graph


INSPECTOR_TABS = (
    "overview",
    "configuration",
    "input",
    "output",
    "evidence",
    "policy",
    "attempts",
    "cost_timing",
    "changes",
    "help",
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            kl = str(k).lower()
            if any(s in kl for s in ("secret", "password", "token", "api_key", "authorization", "prompt")):
                out[k] = "[redacted]"
            elif kl in {"email", "phone"} and isinstance(v, str):
                out[k] = v[:2] + "***" if len(v) > 2 else "***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def build_inspector(
    *,
    mode: str,
    graph: dict[str, Any] | None,
    node_id: str,
    run: dict[str, Any] | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    mode = str(mode or "design")
    graph = graph or {}
    node = next((n for n in (graph.get("nodes") or []) if n.get("id") == node_id), None)
    if not node:
        return {"ok": False, "error_code": "node_not_found", "node_id": node_id}

    validation = validate_graph(graph)
    node_issues = [i for i in validation.get("issues") or [] if node_id in str(i.get("path") or "")]

    ns = ((run or {}).get("node_states") or {}).get(node_id) or {}
    attempts = ns.get("attempts") or []
    last = attempts[-1] if attempts else {}

    config = _redact(node.get("config") or {})
    provenance = {
        "config": "user_supplied",
        "runtime_output": "observed" if mode in {"live", "replay"} else "n/a",
        "model_inference": "never_verified",
    }

    decision_explain = None
    if node.get("family") == "decision":
        decision_explain = {
            "rules_evaluated": config.get("rules") or [{"field": "score", "op": ">=", "value": config.get("threshold")}],
            "branch_result": last.get("detail", {}).get("branch") if isinstance(last.get("detail"), dict) else None,
            "policy_version": "crm-decision-v1",
            "source_ids": [],
            "note": "Concise outcome rationale only; no hidden chain-of-thought.",
        }

    model_info = None
    if node.get("type") in {"enrichment", "discovery"} or "model" in str(node.get("type")):
        model_info = {
            "provider": config.get("provider_ref") or "workspace_default",
            "model": config.get("model_ref") or "[model_ref]",
            "prompt_template_version": config.get("prompt_template_version") or "n/a",
            "token_counts": last.get("detail", {}).get("tokens") if isinstance(last.get("detail"), dict) else None,
            "cost": last.get("detail", {}).get("cost") if isinstance(last.get("detail"), dict) else None,
            "schema_validation": "pending" if mode == "design" else "ok",
            "confidence": last.get("detail", {}).get("confidence") if isinstance(last.get("detail"), dict) else None,
            "safety": "redacted_prompts",
        }

    external = None
    if node.get("family") in {"outreach", "integration", "booking"}:
        external = {
            "destination_category": node.get("type"),
            "idempotency_key": last.get("detail", {}).get("idempotency_key")
            if isinstance(last.get("detail"), dict)
            else None,
            "request_status": ns.get("state"),
            "provider_event_id": last.get("detail", {}).get("provider_event_id")
            if isinstance(last.get("detail"), dict)
            else None,
            "retries": max(0, len(attempts) - 1),
            "response_class": last.get("detail", {}).get("response_class")
            if isinstance(last.get("detail"), dict)
            else None,
        }

    approval = None
    if node.get("type") == "soft_wall_approval":
        approval = {
            "approved_hashes": last.get("detail", {}).get("approved_hashes")
            if isinstance(last.get("detail"), dict)
            else [],
            "invalidated": bool(last.get("detail", {}).get("invalidated"))
            if isinstance(last.get("detail"), dict)
            else False,
            "scope": config.get("scope"),
        }

    contactability = None
    if node.get("type") in {"email_send", "contactability"}:
        contactability = {
            "verdict": last.get("detail", {}).get("contactability")
            if isinstance(last.get("detail"), dict)
            else "unknown",
            "suppression": last.get("detail", {}).get("suppression")
            if isinstance(last.get("detail"), dict)
            else None,
        }

    tabs = {
        "overview": {
            "purpose": node.get("label") or node.get("type"),
            "family": node.get("family"),
            "type": node.get("type"),
            "mode": mode,
            "runtime_state": ns.get("state") or "draft",
        },
        "configuration": config,
        "input": _redact(last.get("detail", {}).get("input") if isinstance(last.get("detail"), dict) else {}),
        "output": _redact(last.get("detail", {}).get("output") if isinstance(last.get("detail"), dict) else {}),
        "evidence": _redact(last.get("detail", {}).get("evidence") if isinstance(last.get("detail"), dict) else []),
        "policy": {
            "decision": decision_explain,
            "approval": approval,
            "contactability": contactability,
            "soft_wall": node.get("type") == "soft_wall_approval",
        },
        "attempts": _redact(attempts),
        "cost_timing": {
            "duration_ms": last.get("detail", {}).get("duration_ms") if isinstance(last.get("detail"), dict) else None,
            "cost": last.get("detail", {}).get("cost") if isinstance(last.get("detail"), dict) else None,
            "model": model_info,
            "external": external,
        },
        "changes": {"note": "Published workflows are immutable; edits create a new draft version."},
        "help": {
            "docs": "/crm/workflows",
            "fix_issues": node_issues,
        },
    }

    links = {
        "workflow": f"/crm/workflows/{graph.get('id')}" if graph.get("id") else "/crm/workflows",
        "run": f"/crm/runs/{run['id']}" if run and run.get("id") else None,
        "record": f"/crm/leads/{run.get('subject_id')}" if run and run.get("subject_id") else None,
        "approvals": "/crm",
        "analytics": "/crm/analytics",
    }

    return {
        "ok": True,
        "mode": mode,
        "node_id": node_id,
        "workspace_id": workspace_id,
        "tabs_order": list(INSPECTOR_TABS),
        "tabs": tabs,
        "provenance": provenance,
        "validation_issues": node_issues,
        "links": links,
        "permissions": {
            "retry": mode in {"live", "replay"} and ns.get("state") == "failed",
            "skip": mode == "live" and ns.get("state") in {"failed", "waiting"},
            "edit_draft": mode == "design",
        },
    }


def create_support_bundle(
    workspace_id: str,
    *,
    graph: dict[str, Any] | None,
    run: dict[str, Any] | None,
    selected_node_ids: list[str] | None = None,
) -> dict[str, Any]:
    bundle_id = str(uuid.uuid4())
    events = []
    if run:
        for e in run.get("events") or []:
            if selected_node_ids and e.get("node_id") not in selected_node_ids:
                continue
            events.append(_redact(e))
    payload = {
        "bundle_id": bundle_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "workspace_id": workspace_id,
        "graph_version": (graph or {}).get("workflow_version"),
        "workflow_id": (graph or {}).get("id") or (run or {}).get("workflow_id"),
        "run_id": (run or {}).get("id"),
        "events": events,
        "errors": [
            e
            for e in events
            if e.get("state") == "failed"
        ],
        "environment": {"product": "keprix", "surface": "crm_visual"},
        "correlation_ids": sorted({str(e.get("correlation_id")) for e in events if e.get("correlation_id")}),
        "redacted": True,
    }
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "crm" / "support_bundles"
    except Exception:
        root = Path.home() / ".keprix" / "crm" / "support_bundles"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{bundle_id}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {"ok": True, "bundle_id": bundle_id, "path": str(path), "redacted": True, "summary": {
        "events": len(events),
        "errors": len(payload["errors"]),
    }}
