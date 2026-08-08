"""ABBIS product pack node catalog for the shared product_sidecar registry."""

from __future__ import annotations

from keprix.product_sidecar.types import CapabilityNode, NodeStatus, RiskClass

_RISK = {
    "read": RiskClass.READ,
    "propose": RiskClass.PROPOSE,
    "mutate": RiskClass.MUTATE,
    "outbound": RiskClass.OUTBOUND,
    "destructive": RiskClass.DESTRUCTIVE,
    "high_risk": RiskClass.HIGH_RISK,
}

_STATUS = {
    "live": NodeStatus.LIVE,
    "stub": NodeStatus.STUB,
    "not_configured": NodeStatus.NOT_CONFIGURED,
    "disabled": NodeStatus.DISABLED,
    "degraded": NodeStatus.DEGRADED,
}


def build_abbis_nodes() -> dict[str, CapabilityNode]:
    specs = [
        ("pipe_count_calculate", "Pipe count calculate", "calculators", "read", "live", False),
        ("pump_yield_calculate", "Pump yield calculate", "calculators", "read", "live", False),
        ("quote_calculate", "Quote calculate", "calculators", "read", "live", False),
        ("job_brief", "Job brief", "field", "read", "live", False),
        ("drilling_log_assist", "Drilling log assist", "field", "propose", "live", True),
        ("stock_usage_propose", "Stock usage propose", "inventory", "propose", "live", True),
        ("rpm_maintenance_assess", "RPM maintenance assess", "fleet", "propose", "live", True),
        ("receipt_draft", "Receipt draft", "finance", "propose", "live", True),
        ("field_report_draft", "Field report draft", "field", "propose", "live", True),
        ("cashflow_explain", "Cashflow explain", "finance", "read", "live", False),
        ("debt_followup_propose", "Debt follow-up propose", "finance", "outbound", "live", True),
        ("supplier_match", "Supplier match", "marketplace", "read", "live", False),
        ("project_risk_summary", "Project risk summary", "projects", "read", "live", False),
        ("compliance_check", "Compliance check", "compliance", "read", "live", False),
        ("tender_support", "Tender support", "business", "propose", "stub", True),
        ("training_recommend", "Training recommend", "workforce", "propose", "live", False),
        ("association_digest", "Association digest", "association", "read", "live", False),
        ("national_aggregate_summary", "National aggregate summary", "national", "read", "live", False),
        ("bdag_intelligence_query", "BDAG intelligence query", "national", "read", "live", False),
    ]
    nodes: dict[str, CapabilityNode] = {}
    for key, title, domain, risk, status, soft_wall in specs:
        nodes[key] = CapabilityNode(
            key=key,
            version="1.0.0",
            title=title,
            product="abbis",
            domain=domain,
            risk=_RISK[risk],
            status=_STATUS[status],
            required_grants=(f"node:{key}",),
            entitlements=("abbis",),
            soft_wall=soft_wall,
            sync=True,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            idempotent=key.endswith("_calculate"),
            operator_guidance="ABBIS Ghana borehole pack; product remains authority",
        )
    return nodes
