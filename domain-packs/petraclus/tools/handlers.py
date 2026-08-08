"""Petraclus sidecar tool handlers (reads, analysis, proposals, gated actions)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from connector.fixture_product_api import (
    ASSETS,
    EVIDENCE,
    FINDINGS,
    TARGET_GRANTS,
    WORKSPACES,
    _FINDING_STATE,
    _REPORTS,
    _SCANS,
    _entitlements,
    reset_fixture_state,
)
from isolation import IsolationContext, IsolationDenied, IsolationEnforcer, TargetGrant
from nodes.catalog import FORBIDDEN_NODES, all_nodes, is_action_node
from tools.safety import (
    assert_no_forbidden_nodes,
    detect_prompt_injection,
    safe_log_fields,
    sanitize_scanner_text,
)

_ENFORCER = IsolationEnforcer()
_SOURCE = "keprix-petraclus"
_HANDLER_LOGS: list[dict[str, Any]] = []


def clear_handler_logs() -> None:
    _HANDLER_LOGS.clear()


def get_handler_logs() -> list[dict[str, Any]]:
    return list(_HANDLER_LOGS)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _grant_from_id(grant_id: str | None) -> TargetGrant | None:
    if not grant_id:
        return None
    row = TARGET_GRANTS.get(grant_id)
    if not row:
        return None
    return TargetGrant(
        grant_id=row["id"],
        workspace_id=row["workspace_id"],
        target_type=row["target_type"],
        target_value=row["target_value"],
        resolved_addresses=list(row.get("resolved_addresses") or []),
        ports=list(row.get("ports") or []),
        protocols=list(row.get("protocols") or []),
        allowed_techniques=list(row.get("allowed_techniques") or []),
        excluded_ranges=list(row.get("excluded_ranges") or []),
        window_start=str(row.get("window_start") or ""),
        window_end=str(row.get("window_end") or ""),
        owner_evidence=str(row.get("owner_evidence") or ""),
        approver=str(row.get("approver") or ""),
        expiry=str(row.get("expiry") or ""),
        revoked=bool(row.get("revoked")),
        allows_internal=bool(row.get("allows_internal")),
    )


def _ctx_from_args(args: dict[str, Any]) -> IsolationContext:
    workspace_id = str(args.get("workspace_id") or args.get("tenant_id") or "")
    grants = args.get("grants") or []
    edition = str(args.get("edition") or "")
    if not edition and workspace_id in WORKSPACES:
        edition = WORKSPACES[workspace_id]["edition"]
    if not edition:
        edition = "community"
    grant = _grant_from_id(args.get("target_grant_id"))
    return IsolationContext(
        product=str(args.get("product") or "petraclus"),
        workspace_id=workspace_id,
        tenant_id=workspace_id,
        edition=edition,
        role=str(args.get("role") or "analyst"),
        grants=frozenset(str(g) for g in grants),
        purpose=str(args.get("purpose") or "invoke"),
        actor_id=str(args.get("actor_id") or ""),
        target_grant=grant,
    )


def _guard(node_key: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        assert_no_forbidden_nodes(node_key)
    except PermissionError as exc:
        return {"ok": False, "error": str(exc), "layer": "role_grants", "reason": "forbidden_node"}
    ctx = _ctx_from_args(args)
    if not ctx.workspace_id:
        ctx.workspace_id = "ws-alpha"
        ctx.tenant_id = "ws-alpha"
        if not ctx.grants:
            ctx.grants = frozenset({"node:*", "mutate"})
        if not ctx.edition:
            ctx.edition = "community"
    grant = ctx.target_grant
    try:
        return _ENFORCER.enforce(
            ctx,
            node_key=node_key,
            record_workspace=args.get("record_workspace"),
            grant=grant,
        )
    except IsolationDenied as exc:
        return {"ok": False, "error": str(exc), "layer": exc.layer, "reason": exc.reason}


def _provenance(
    *,
    observed: dict[str, Any] | None = None,
    feed: dict[str, Any] | None = None,
    inferred: dict[str, Any] | None = None,
    human: dict[str, Any] | None = None,
    asset_ids: list[str] | None = None,
    finding_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "observed_scanner_fact": observed or {},
        "feed_data": feed or {},
        "model_inference": inferred or {},
        "human_verification": human or {},
        "cited_ids": {
            "asset_ids": asset_ids or [],
            "finding_ids": finding_ids or [],
            "evidence_ids": evidence_ids or [],
        },
    }


def _log(node_key: str, args: dict[str, Any], result_meta: dict[str, Any]) -> None:
    _HANDLER_LOGS.append(
        {
            "node": node_key,
            "at": _iso_now(),
            "fields": safe_log_fields(
                {
                    "workspace_id": args.get("workspace_id"),
                    "finding_id": args.get("finding_id"),
                    "status": result_meta.get("status"),
                    "token": args.get("token"),
                    "description": args.get("description"),
                }
            ),
        }
    )


def _err(guard: dict[str, Any]) -> str:
    return json.dumps({"status": "error", **guard})


def _ok(payload: dict[str, Any]) -> str:
    out = dict(payload)
    out.setdefault("source", _SOURCE)
    out.setdefault("at", _iso_now())
    out.setdefault("status", "ok")
    return json.dumps(out)


# ---- READS ----

def asset_get_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("asset_get", args)
    if not guard.get("ok"):
        return _err(guard)
    asset_id = str(args.get("asset_id") or "")
    asset = ASSETS.get(asset_id)
    if not asset or asset["workspace_id"] != (_ctx_from_args(args).workspace_id or "ws-alpha"):
        ws = args.get("workspace_id") or "ws-alpha"
        if not asset or asset["workspace_id"] != ws:
            return json.dumps({"status": "error", "error": "asset_not_found_or_cross_workspace"})
    _log("asset_get", args, {"status": "ok"})
    return _ok(
        {
            "asset": asset,
            "provenance": _provenance(observed={"asset_id": asset_id}, asset_ids=[asset_id]),
        }
    )


def scan_get_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("scan_get", args)
    if not guard.get("ok"):
        return _err(guard)
    scan = _SCANS.get(str(args.get("scan_id") or ""))
    ws = args.get("workspace_id") or "ws-alpha"
    if not scan or scan["workspace_id"] != ws:
        return json.dumps({"status": "error", "error": "scan_not_found_or_cross_workspace"})
    return _ok({"scan": scan, "provenance": _provenance(observed={"scan_id": scan["id"]})})


def finding_get_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("finding_get", args)
    if not guard.get("ok"):
        return _err(guard)
    finding = _FINDING_STATE.get(str(args.get("finding_id") or ""))
    ws = args.get("workspace_id") or "ws-alpha"
    if not finding or finding["workspace_id"] != ws:
        return json.dumps({"status": "error", "error": "finding_not_found_or_cross_workspace"})
    sanitized = sanitize_scanner_text(str(finding.get("description") or ""))
    safe_finding = dict(finding)
    safe_finding["description"] = sanitized["text"]
    safe_finding["injection"] = sanitized["injection"]
    _log("finding_get", args, {"status": "ok"})
    return _ok(
        {
            "finding": safe_finding,
            "provenance": _provenance(
                observed={
                    "severity": finding.get("severity"),
                    "verified_state": finding.get("verified_state"),
                    "cve": finding.get("cve"),
                    "cwe": finding.get("cwe"),
                    "cvss": finding.get("cvss"),
                },
                finding_ids=[finding["id"]],
                asset_ids=[finding.get("asset_id") or ""],
                evidence_ids=list(finding.get("evidence_ids") or []),
            ),
            "tool_triggered_from_injection": False,
        }
    )


def finding_search_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("finding_search", args)
    if not guard.get("ok"):
        return _err(guard)
    ws = args.get("workspace_id") or "ws-alpha"
    items = []
    for finding in _FINDING_STATE.values():
        if finding["workspace_id"] != ws:
            continue
        row = dict(finding)
        row["description"] = sanitize_scanner_text(str(row.get("description") or ""))["text"]
        items.append(row)
    return _ok(
        {
            "findings": items,
            "provenance": _provenance(
                observed={"count": len(items)},
                finding_ids=[f["id"] for f in items],
            ),
        }
    )


def evidence_get_redacted_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("evidence_get_redacted", args)
    if not guard.get("ok"):
        return _err(guard)
    evidence = EVIDENCE.get(str(args.get("evidence_id") or ""))
    ws = args.get("workspace_id") or "ws-alpha"
    if not evidence or evidence["workspace_id"] != ws:
        return json.dumps({"status": "error", "error": "evidence_not_found_or_cross_workspace"})
    size = int(args.get("max_bytes") or 512_000)
    summary = str(evidence.get("summary") or "")
    if len(summary.encode("utf-8")) > size or args.get("oversized"):
        return json.dumps({"status": "error", "error": "evidence_too_large"})
    out = dict(evidence)
    out["raw"] = None
    out["redacted"] = True
    return _ok({"evidence": out, "redacted": True, "provenance": _provenance(observed={"evidence_id": out["id"]}, evidence_ids=[out["id"]])})


def report_get_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("report_get", args)
    if not guard.get("ok"):
        return _err(guard)
    report = _REPORTS.get(str(args.get("report_id") or ""))
    ws = args.get("workspace_id") or "ws-alpha"
    if not report or report["workspace_id"] != ws:
        return json.dumps({"status": "error", "error": "report_not_found_or_cross_workspace"})
    return _ok({"report": report, "provenance": _provenance(observed={"report_id": report["id"]})})


def audit_get_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("audit_get", args)
    if not guard.get("ok"):
        return _err(guard)
    ws = args.get("workspace_id") or "ws-alpha"
    edition = WORKSPACES.get(ws, {}).get("edition", "community")
    if edition == "community":
        return json.dumps({"status": "error", "error": "edition_denied", "layer": "edition"})
    return _ok({"events": [{"id": "audit-1", "workspace_id": ws, "type": "finding.read"}]})


def integration_health_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("integration_health", args)
    if not guard.get("ok"):
        return _err(guard)
    return _ok(
        {
            "integrations": {
                "product_api": "ok",
                "scanner": "ok",
                "feed": "degraded",
                "model": "ok",
                "licence": "ok",
            }
        }
    )


# ---- ANALYSIS ----

def _load_finding(args: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    finding = _FINDING_STATE.get(str(args.get("finding_id") or ""))
    ws = args.get("workspace_id") or "ws-alpha"
    if not finding or finding["workspace_id"] != ws:
        return None, "finding_not_found_or_cross_workspace"
    return finding, None


def finding_explain_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("finding_explain", args)
    if not guard.get("ok"):
        return _err(guard)
    finding, err = _load_finding(args)
    if err:
        return json.dumps({"status": "error", "error": err})
    assert finding is not None
    sanitized = sanitize_scanner_text(str(finding.get("description") or ""))
    injection = sanitized["injection"]
    explanation = {
        "what": finding.get("title"),
        "evidence_summary": "Redacted evidence cited; raw banners treated as untrusted.",
        "why_it_matters": "Prioritise based on asset exposure and known CVEs without changing scanner severity.",
        "confidence": "medium",
        "safe_verification": "Re-check with authorised non-destructive verification only.",
        "remediation_hint": "Proposal only; apply via Petraclus workflows.",
        "injection_ignored": injection["detected"],
        "tool_triggered_from_injection": False,
    }
    if injection["detected"]:
        explanation["note"] = "Prompt injection signals in finding text were ignored; no tools invoked."
    return _ok(
        {
            "explanation": explanation,
            "scanner_severity_unchanged": finding.get("severity"),
            "verified_state_unchanged": finding.get("verified_state"),
            "provenance": _provenance(
                observed={
                    "severity": finding.get("severity"),
                    "cve": finding.get("cve"),
                    "cwe": finding.get("cwe"),
                    "cvss": finding.get("cvss"),
                },
                inferred={"confidence": "medium", "narrative": explanation["why_it_matters"]},
                finding_ids=[finding["id"]],
                asset_ids=[finding.get("asset_id") or ""],
                evidence_ids=list(finding.get("evidence_ids") or []),
            ),
        }
    )


def severity_review_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("severity_review", args)
    if not guard.get("ok"):
        return _err(guard)
    finding, err = _load_finding(args)
    if err:
        return json.dumps({"status": "error", "error": err})
    assert finding is not None
    # Models propose; cannot silently change scanner severity
    proposed = args.get("proposed_severity")
    review = {
        "scanner_severity": finding.get("severity"),
        "proposed_severity": proposed if proposed else finding.get("severity"),
        "severity_changed_by_model": False,
        "rationale": "Grounded on scanner CVSS/CWE; human must confirm any change.",
        "cve": finding.get("cve"),
        "cwe": finding.get("cwe"),
        "cvss": finding.get("cvss"),
    }
    return _ok(
        {
            "review": review,
            "provenance": _provenance(
                observed={
                    "severity": finding.get("severity"),
                    "cvss": finding.get("cvss"),
                    "cve": finding.get("cve"),
                    "cwe": finding.get("cwe"),
                },
                inferred={"proposed_severity": review["proposed_severity"]},
                finding_ids=[finding["id"]],
                asset_ids=[finding.get("asset_id") or ""],
                evidence_ids=list(finding.get("evidence_ids") or []),
            ),
        }
    )


def false_positive_propose_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("false_positive_propose", args)
    if not guard.get("ok"):
        return _err(guard)
    finding, err = _load_finding(args)
    if err:
        return json.dumps({"status": "error", "error": err})
    assert finding is not None
    payload = {"finding_id": finding["id"], "proposal": "mark_false_positive", "reason": args.get("reason") or "fixture"}
    return _ok(
        {
            "proposal": payload,
            "preview_hash": _preview_hash(payload),
            "soft_wall": True,
            "provenance": _provenance(inferred=payload, finding_ids=[finding["id"]]),
        }
    )


def attack_path_summarise_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("attack_path_summarise", args)
    if not guard.get("ok"):
        return _err(guard)
    return _ok(
        {
            "summary": "Limited attack path sketch from authorised findings only.",
            "exploit_automation": False,
            "provenance": _provenance(inferred={"path_confidence": "low"}),
        }
    )


def control_map_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("control_map", args)
    if not guard.get("ok"):
        return _err(guard)
    finding, err = _load_finding(args)
    controls = [{"framework": "CIS", "control": "4.1", "status": "gap_possible"}]
    return _ok(
        {
            "controls": controls,
            "provenance": _provenance(
                inferred={"controls": controls},
                finding_ids=[finding["id"]] if finding else [],
            ),
        }
    )


def remediation_plan_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("remediation_plan", args)
    if not guard.get("ok"):
        return _err(guard)
    finding, err = _load_finding(args)
    plan = {
        "steps": ["Confirm finding", "Propose patch/config change", "Retest under grant"],
        "execute_allowed": False,
        "note": "Remediation is proposal-only.",
    }
    return _ok(
        {
            "plan": plan,
            "provenance": _provenance(inferred=plan, finding_ids=[finding["id"]] if finding else []),
        }
    )


def executive_summary_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("executive_summary", args)
    if not guard.get("ok"):
        return _err(guard)
    ws = args.get("workspace_id") or "ws-alpha"
    findings = [f for f in _FINDING_STATE.values() if f["workspace_id"] == ws]
    summary = {
        "open_findings": len(findings),
        "headline": f"{len(findings)} authorised findings in workspace scope",
    }
    return _ok(
        {
            "summary": summary,
            "provenance": _provenance(
                observed={"count": len(findings)},
                inferred=summary,
                finding_ids=[f["id"] for f in findings],
            ),
        }
    )


def report_draft_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("report_draft", args)
    if not guard.get("ok"):
        return _err(guard)
    draft = {
        "title": args.get("title") or "Draft security report",
        "sections": ["executive", "technical", "provenance"],
        "status": "draft",
    }
    return _ok({"draft": draft, "preview_hash": _preview_hash(draft), "soft_wall": True, "provenance": _provenance(inferred=draft)})


def feed_item_assess_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("feed_item_assess", args)
    if not guard.get("ok"):
        return _err(guard)
    text = str(args.get("feed_text") or args.get("text") or "")
    sanitized = sanitize_scanner_text(text)
    return _ok(
        {
            "assessment": {
                "relevant": not sanitized["injection"]["detected"],
                "injection_detected": sanitized["injection"]["detected"],
                "tool_triggered_from_injection": False,
            },
            "provenance": _provenance(feed={"text_sanitized": sanitized["text"][:200]}, inferred={"relevant": True}),
        }
    )


def query_findings_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("query_findings", args)
    if not guard.get("ok"):
        return _err(guard)
    return finding_search_handler(args)


# ---- PROPOSALS ----

def scan_plan_propose_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("scan_plan_propose", args)
    if not guard.get("ok"):
        return _err(guard)
    grant = _grant_from_id(args.get("target_grant_id"))
    try:
        validated = _ENFORCER.revalidate_target_grant(grant)
    except IsolationDenied as exc:
        return _err({"ok": False, "error": str(exc), "layer": exc.layer, "reason": exc.reason})
    plan = {
        "targets": [validated.target_value],
        "resolved_addresses": validated.resolved_addresses,
        "ports": validated.ports,
        "methods": validated.allowed_techniques,
        "exclusions": validated.excluded_ranges,
        "timing": "off_peak",
        "traffic_estimate": "low",
        "possible_impact": "banner_grab_and_port_probe",
    }
    return _ok({"plan": plan, "preview_hash": _preview_hash(plan), "soft_wall": True, "provenance": _provenance(inferred=plan)})


def finding_triage_propose_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("finding_triage_propose", args)
    if not guard.get("ok"):
        return _err(guard)
    finding, err = _load_finding(args)
    if err:
        return json.dumps({"status": "error", "error": err})
    assert finding is not None
    proposal = {"finding_id": finding["id"], "priority": "p2", "action": "investigate"}
    return _ok({"proposal": proposal, "preview_hash": _preview_hash(proposal), "soft_wall": True, "provenance": _provenance(inferred=proposal, finding_ids=[finding["id"]])})


def remediation_change_propose_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("remediation_change_propose", args)
    if not guard.get("ok"):
        return _err(guard)
    proposal = {"change": args.get("change") or "disable_weak_cipher", "execute_allowed": False}
    return _ok({"proposal": proposal, "preview_hash": _preview_hash(proposal), "soft_wall": True, "provenance": _provenance(inferred=proposal)})


def exception_propose_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("exception_propose", args)
    if not guard.get("ok"):
        return _err(guard)
    proposal = {"exception": args.get("reason") or "accepted_risk", "ttl_days": 30}
    return _ok({"proposal": proposal, "preview_hash": _preview_hash(proposal), "soft_wall": True, "provenance": _provenance(inferred=proposal)})


def ticket_propose_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("ticket_propose", args)
    if not guard.get("ok"):
        return _err(guard)
    proposal = {"title": args.get("title") or "Security finding", "finding_ids": args.get("finding_ids") or []}
    return _ok({"proposal": proposal, "preview_hash": _preview_hash(proposal), "soft_wall": True, "provenance": _provenance(inferred=proposal)})


# ---- ACTIONS ----

_APPROVALS: dict[str, dict[str, Any]] = {}


def register_local_approval(approval_id: str, *, workspace_id: str, input_hash: str, approved: bool = True) -> None:
    _APPROVALS[approval_id] = {
        "approval_id": approval_id,
        "workspace_id": workspace_id,
        "input_hash": input_hash,
        "status": "approved" if approved else "rejected",
    }


def _require_action_authority(args: dict[str, Any], node_key: str) -> dict[str, Any] | None:
    approval_id = str(args.get("approval_id") or "")
    input_hash = str(args.get("input_hash") or "")
    if not approval_id or not input_hash:
        return {"ok": False, "error": "approval_id_and_input_hash_required", "layer": "approval", "reason": "missing"}
    row = _APPROVALS.get(approval_id)
    if not row or row.get("status") != "approved" or row.get("input_hash") != input_hash:
        return {"ok": False, "error": "stale_or_missing_approval", "layer": "approval", "reason": "stale"}
    ws = args.get("workspace_id") or "ws-alpha"
    if row.get("workspace_id") and row["workspace_id"] != ws:
        return {"ok": False, "error": "cross_workspace", "layer": "workspace_tenant", "reason": "cross_workspace"}
    entitlements = _entitlements(WORKSPACES.get(ws, {}).get("edition", "community"))
    if node_key == "scan_start" and not entitlements["entitlements"].get("active_scan"):
        return {"ok": False, "error": "licence_denied", "layer": "edition", "reason": "licence"}
    if node_key in {"ticket_create", "report_publish"} and WORKSPACES.get(ws, {}).get("edition") == "community":
        return {"ok": False, "error": "edition_denied", "layer": "edition", "reason": "edition"}
    return None


def scan_start_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("scan_start", args)
    if not guard.get("ok"):
        return _err(guard)
    auth = _require_action_authority(args, "scan_start")
    if auth:
        return _err(auth)
    grant = _grant_from_id(args.get("target_grant_id"))
    try:
        _ENFORCER.revalidate_target_grant(grant)
    except IsolationDenied as exc:
        return _err({"ok": False, "error": str(exc), "layer": exc.layer, "reason": exc.reason})
    assert grant is not None
    scan_id = f"scan_{uuid.uuid4().hex[:10]}"
    row = {
        "id": scan_id,
        "workspace_id": args.get("workspace_id") or "ws-alpha",
        "status": "running",
        "target_grant_id": grant.grant_id,
    }
    _SCANS[scan_id] = row
    _log("scan_start", args, {"status": "running"})
    return _ok({"scan_id": scan_id, "status": "running"})


def scan_cancel_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("scan_cancel", args)
    if not guard.get("ok"):
        return _err(guard)
    auth = _require_action_authority(args, "scan_cancel")
    if auth:
        return _err(auth)
    scan_id = str(args.get("scan_id") or "")
    scan = _SCANS.get(scan_id)
    ws = args.get("workspace_id") or "ws-alpha"
    if not scan or scan["workspace_id"] != ws:
        return json.dumps({"status": "error", "error": "scan_not_found_or_cross_workspace"})
    scan["status"] = "cancelled"
    return _ok({"scan_id": scan_id, "status": "cancelled"})


def finding_update_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("finding_update", args)
    if not guard.get("ok"):
        return _err(guard)
    auth = _require_action_authority(args, "finding_update")
    if auth:
        return _err(auth)
    finding, err = _load_finding(args)
    if err:
        return json.dumps({"status": "error", "error": err})
    assert finding is not None
    # Model cannot silently change severity; only explicit transition field with approval
    if args.get("severity") and args.get("severity") != finding.get("severity"):
        if not args.get("human_confirmed_severity_change"):
            return json.dumps({"status": "error", "error": "model_cannot_silently_change_severity"})
    transition = str(args.get("transition") or args.get("verified_state") or finding.get("verified_state"))
    finding["verified_state"] = transition
    return _ok({"status": "updated", "finding_id": finding["id"], "verified_state": transition})


def ticket_create_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("ticket_create", args)
    if not guard.get("ok"):
        return _err(guard)
    auth = _require_action_authority(args, "ticket_create")
    if auth:
        return _err(auth)
    ticket_id = f"tkt_{uuid.uuid4().hex[:10]}"
    return _ok({"ticket_id": ticket_id, "status": "created"})


def report_publish_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("report_publish", args)
    if not guard.get("ok"):
        return _err(guard)
    auth = _require_action_authority(args, "report_publish")
    if auth:
        return _err(auth)
    report_id = str(args.get("report_id") or "")
    report = _REPORTS.get(report_id)
    ws = args.get("workspace_id") or "ws-alpha"
    if not report or report["workspace_id"] != ws:
        return json.dumps({"status": "error", "error": "report_not_found_or_cross_workspace"})
    report["status"] = "published"
    return _ok({"status": "published", "report_id": report_id})


def playbook_compose_handler(args: dict[str, Any], **_: Any) -> str:
    """Reject action nodes when grants lack mutate even via playbook composition."""
    nodes = list(args.get("nodes") or [])
    for node_key in nodes:
        if node_key in FORBIDDEN_NODES:
            return json.dumps({"status": "error", "error": f"forbidden_node:{node_key}"})
        if is_action_node(node_key):
            guard = _guard(node_key, args)
            if not guard.get("ok"):
                return _err(guard)
    return _ok({"composed": nodes, "note": "composition revalidated each node"})
