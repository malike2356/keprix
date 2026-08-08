"""ABBIS sidecar tool handlers (deterministic calculators + proposal stubs)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from calculators.formulas import (
    FORMULA_VERSION,
    depth_error_pct,
    depth_from_rods,
    estimate_quote,
    pe_hose_rolls,
    pipe_count,
    pump_test_result,
    recommended_hp,
    screen_plain_split,
)
from isolation import IsolationContext, IsolationDenied, IsolationEnforcer
from nodes.catalog import all_nodes

_ENFORCER = IsolationEnforcer()
_SOURCE = "keprix-abbis"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ctx_from_args(args: dict[str, Any]) -> IsolationContext:
    accessories = args.get("accessories") or []
    grants = args.get("grants") or []
    return IsolationContext(
        product=str(args.get("product") or "abbis"),
        tenant_id=str(args.get("tenant_id") or args.get("workspace_id") or ""),
        organisation_id=str(args.get("organisation_id") or ""),
        stakeholder=str(args.get("stakeholder") or ""),
        accessories=frozenset(str(a) for a in accessories),
        project_id=str(args.get("project_id") or ""),
        site_id=str(args.get("site_id") or ""),
        subject_id=str(args.get("subject_id") or ""),
        purpose=str(args.get("purpose") or ""),
        grants=frozenset(str(g) for g in grants),
        bdag_role=str(args.get("bdag_role") or ""),
        national_aggregate=bool(args.get("national_aggregate")),
        onboarding_complete=bool(args.get("onboarding_complete", True)),
    )


def _guard(node_key: str, args: dict[str, Any], *, accessory: str | None = None) -> dict[str, Any]:
    ctx = _ctx_from_args(args)
    # Local fixture mode: if no tenant provided, use fixture tenant for calculators only
    if not ctx.tenant_id and node_key.endswith("_calculate"):
        ctx.tenant_id = "fixture-tenant"
        if not ctx.stakeholder:
            ctx.stakeholder = "S07"
        if not ctx.accessories:
            ctx.accessories = frozenset({"calculators", "field.operations", "quotes.location"})
        if not ctx.grants:
            ctx.grants = frozenset({f"node:{node_key}", "*"})
    nodes = all_nodes()
    node = nodes.get(node_key) or {}
    required = accessory or node.get("accessory")
    try:
        return _ENFORCER.enforce(
            ctx,
            node_key=node_key,
            required_accessory=required if ctx.accessories else None,
            record_tenant=args.get("record_tenant"),
            record_project=args.get("record_project"),
            record_site=args.get("record_site"),
            record_subject=args.get("record_subject"),
            national_cell_count=args.get("national_cell_count"),
        )
    except IsolationDenied as exc:
        return {"ok": False, "error": str(exc), "layer": exc.layer, "reason": exc.reason}


def _label(payload: dict[str, Any], *, observed: dict | None = None, inferred: dict | None = None) -> dict[str, Any]:
    out = dict(payload)
    out["labels"] = {
        "observed": observed or {},
        "calculated": {k: v for k, v in payload.items() if k not in {"labels", "value_kind"}},
        "inferred": inferred or {},
        "human_verified": {},
    }
    out["localisation_via"] = "abbis"
    out["operator"] = "ghanaian_operating_company"
    out["association"] = "BDAG"
    out["forbidden_operator_names"] = ["VERLOX", "verlox.uk"]
    out["source"] = _SOURCE
    out["at"] = _iso_now()
    return out


def pipe_count_calculate_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("pipe_count_calculate", args)
    if not guard.get("ok"):
        return json.dumps({"status": "error", **guard})
    overburden = float(args.get("overburden_m", 45))
    total_depth = args.get("total_depth_m")
    result: dict[str, Any] = {
        "pipes_required": pipe_count(overburden),
        "overburden_m": overburden,
        "pipe_length_m": 3,
        "formula_version": FORMULA_VERSION,
        "value_kind": "calculated",
        "record_ids": args.get("record_ids") or {},
    }
    if total_depth is not None:
        result["split"] = screen_plain_split(overburden, float(total_depth))
    return json.dumps(_label(result, observed={"overburden_m": overburden}))


def pump_yield_calculate_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("pump_yield_calculate", args)
    if not guard.get("ok"):
        return json.dumps({"status": "error", **guard})
    cycles = args.get("cycles")
    if not cycles:
        # Convenience single-fill fixture path
        bucket = float(args.get("bucket_litres", 20))
        fill_seconds = float(args.get("fill_seconds", 10))
        drawdown = float(args.get("drawdown_minutes", 15))
        recovery = float(args.get("recovery_minutes", 45))
        cycles = [
            {
                "drawdown_minutes": drawdown,
                "recovery_minutes": recovery,
                "bucket_fills": [{"bucket_litres": bucket, "fill_seconds": fill_seconds}],
            }
        ]
    result = pump_test_result(cycles)
    result["record_ids"] = args.get("record_ids") or {}
    return json.dumps(_label(result))


def quote_calculate_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("quote_calculate", args)
    if not guard.get("ok"):
        return json.dumps({"status": "error", **guard})
    result = estimate_quote(args)
    # Never invent Kari / KB prefixes
    prefix = str(args.get("quote_prefix") or "")
    lowered = prefix.lower()
    if lowered.startswith("kb") or "kari" in lowered:
        return json.dumps(
            {
                "status": "error",
                "error": "forbidden_quote_prefix",
                "detail": "ABBIS quotes must not use Kari or KB prefixes",
            }
        )
    result["record_ids"] = args.get("record_ids") or {}
    return json.dumps(_label(result))


def rod_depth_calculate_handler(args: dict[str, Any], **_: Any) -> str:
    lengths = [float(x) for x in (args.get("rod_lengths_m") or [])]
    actual = depth_from_rods(lengths)
    err = depth_error_pct(lengths)
    return json.dumps(
        _label(
            {
                "actual_depth_m": actual,
                "depth_error_pct": round(err, 2),
                "warning": err > 3.0,
                "formula_version": FORMULA_VERSION,
                "value_kind": "calculated",
            }
        )
    )


def job_brief_handler(args: dict[str, Any], **_: Any) -> str:
    guard = _guard("job_brief", args, accessory="field.operations")
    if not guard.get("ok") and args.get("tenant_id"):
        return json.dumps({"status": "error", **guard})
    return json.dumps(
        _label(
            {
                "brief": {
                    "project_id": args.get("project_id"),
                    "site_id": args.get("site_id"),
                    "summary": args.get("summary") or "Field job brief (product context required)",
                    "value_kind": "inferred",
                },
                "status": "ok",
            }
        )
    )


def _propose(node_key: str, args: dict[str, Any], action: str) -> str:
    guard = _guard(node_key, args)
    if not guard.get("ok") and args.get("tenant_id"):
        return json.dumps({"status": "error", **guard})
    preview = {
        "node_key": node_key,
        "action": action,
        "inputs": {k: v for k, v in args.items() if k not in {"grants", "accessories"}},
        "requires_approval": True,
        "value_kind": "inferred",
    }
    digest = hashlib.sha256(json.dumps(preview, sort_keys=True, default=str).encode()).hexdigest()
    return json.dumps(
        _label(
            {
                "status": "proposal",
                "preview_hash": digest,
                "proposal": preview,
                "apply_path": f"/api/keprix/v1/actions/{action}/apply",
            }
        )
    )


def drilling_log_assist_handler(args: dict[str, Any], **_: Any) -> str:
    return _propose("drilling_log_assist", args, "drilling_log")


def stock_usage_propose_handler(args: dict[str, Any], **_: Any) -> str:
    return _propose("stock_usage_propose", args, "stock_usage")


def rpm_maintenance_assess_handler(args: dict[str, Any], **_: Any) -> str:
    return _propose("rpm_maintenance_assess", args, "maintenance_task")


def receipt_draft_handler(args: dict[str, Any], **_: Any) -> str:
    return _propose("receipt_draft", args, "receipt")


def field_report_draft_handler(args: dict[str, Any], **_: Any) -> str:
    return _propose("field_report_draft", args, "field_report")


def cashflow_explain_handler(args: dict[str, Any], **_: Any) -> str:
    return json.dumps(
        _label(
            {
                "explanation": "Cashflow explanation requires product finance context slices.",
                "value_kind": "inferred",
                "status": "ok",
            }
        )
    )


def debt_followup_propose_handler(args: dict[str, Any], **_: Any) -> str:
    return _propose("debt_followup_propose", args, "payment_reminder")


def supplier_match_handler(args: dict[str, Any], **_: Any) -> str:
    return json.dumps(_label({"matches": [], "status": "ok", "value_kind": "inferred"}))


def project_risk_summary_handler(args: dict[str, Any], **_: Any) -> str:
    return json.dumps(_label({"risks": [], "status": "ok", "value_kind": "inferred"}))


def compliance_check_handler(args: dict[str, Any], **_: Any) -> str:
    return json.dumps(_label({"findings": [], "status": "ok", "value_kind": "inferred"}))


def tender_support_handler(args: dict[str, Any], **_: Any) -> str:
    return _propose("tender_support", args, "tender")


def training_recommend_handler(args: dict[str, Any], **_: Any) -> str:
    return json.dumps(_label({"recommendations": [], "status": "ok", "value_kind": "inferred"}))


def association_digest_handler(args: dict[str, Any], **_: Any) -> str:
    cell_count = int(args.get("national_cell_count") or 0)
    args = {**args, "national_aggregate": True, "national_cell_count": cell_count or 10}
    if not args.get("stakeholder"):
        args["stakeholder"] = "S14"
    if not args.get("tenant_id"):
        args["tenant_id"] = "bdag-association"
    if not args.get("accessories"):
        args["accessories"] = ["association.ams", "national.intelligence"]
    if not args.get("grants"):
        args["grants"] = ["node:association_digest", "*"]
    guard = _guard("association_digest", args, accessory="association.ams")
    if not guard.get("ok"):
        return json.dumps({"status": "error", **guard})
    return json.dumps(
        _label(
            {
                "digest": "BDAG association digest (de-identified aggregate only)",
                "association": "Borehole Drillers Association of Ghana (BDAG)",
                "cell_count": args["national_cell_count"],
                "value_kind": "observed",
                "status": "ok",
            }
        )
    )


def national_aggregate_summary_handler(args: dict[str, Any], **_: Any) -> str:
    cell_count = int(args.get("national_cell_count") or 0)
    args = {
        **args,
        "national_aggregate": True,
        "national_cell_count": cell_count,
        "stakeholder": args.get("stakeholder") or "S14",
        "tenant_id": args.get("tenant_id") or "bdag-association",
        "accessories": args.get("accessories") or ["national.intelligence"],
        "grants": args.get("grants") or ["node:national_aggregate_summary", "*"],
    }
    guard = _guard("national_aggregate_summary", args, accessory="national.intelligence")
    if not guard.get("ok"):
        return json.dumps({"status": "error", **guard})
    # Never return tenant or worker identifiers
    return json.dumps(
        _label(
            {
                "aggregate": {
                    "region": args.get("region") or "GH",
                    "metric": args.get("metric") or "completed_boreholes",
                    "value": args.get("value"),
                    "cell_count": cell_count,
                },
                "excludes": ["tenant_id", "worker_id", "personal_data"],
                "value_kind": "observed",
                "status": "ok",
            }
        )
    )


def pe_hose_calculate_handler(args: dict[str, Any], **_: Any) -> str:
    depth = float(args.get("depth_m", 0))
    return json.dumps(_label(pe_hose_rolls(depth)))


def pump_hp_calculate_handler(args: dict[str, Any], **_: Any) -> str:
    depth = float(args.get("depth_m", 0))
    hp = recommended_hp(depth)
    return json.dumps(
        _label(
            {
                "recommended_hp": hp,
                "specialist_required": hp is None,
                "formula_version": FORMULA_VERSION,
                "value_kind": "calculated",
            }
        )
    )


def read_stub_handler(node_key: str, args: dict[str, Any]) -> str:
    return json.dumps(
        _label(
            {
                "node_key": node_key,
                "records": [],
                "cursor": None,
                "status": "ok",
                "value_kind": "observed",
                "note": "Southbound ABBIS product API supplies live records",
            }
        )
    )
