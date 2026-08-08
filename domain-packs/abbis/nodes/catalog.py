"""ABBIS capability node catalog for the product sidecar."""

from __future__ import annotations

from typing import Any

# Mirrors keprix.product_sidecar.types without requiring package import at pack load time.

FIELD_NODES: list[dict[str, Any]] = [
    {
        "key": "job_brief",
        "title": "Job brief",
        "domain": "field",
        "risk": "read",
        "status": "live",
        "accessory": "field.operations",
        "sync": True,
    },
    {
        "key": "drilling_log_assist",
        "title": "Drilling log assist",
        "domain": "field",
        "risk": "propose",
        "status": "live",
        "accessory": "field.operations",
        "soft_wall": True,
        "sync": True,
    },
    {
        "key": "pipe_count_calculate",
        "title": "Pipe count calculate",
        "domain": "calculators",
        "risk": "read",
        "status": "live",
        "accessory": "calculators",
        "sync": True,
        "idempotent": True,
    },
    {
        "key": "pump_yield_calculate",
        "title": "Pump yield calculate",
        "domain": "calculators",
        "risk": "read",
        "status": "live",
        "accessory": "calculators",
        "sync": True,
        "idempotent": True,
    },
    {
        "key": "quote_calculate",
        "title": "Quote calculate",
        "domain": "calculators",
        "risk": "read",
        "status": "live",
        "accessory": "calculators",
        "sync": True,
        "idempotent": True,
    },
    {
        "key": "stock_usage_propose",
        "title": "Stock usage propose",
        "domain": "inventory",
        "risk": "propose",
        "status": "live",
        "accessory": "inventory.pos",
        "soft_wall": True,
        "sync": True,
    },
    {
        "key": "rpm_maintenance_assess",
        "title": "RPM maintenance assess",
        "domain": "fleet",
        "risk": "propose",
        "status": "live",
        "accessory": "fleet.maintenance",
        "soft_wall": True,
        "sync": True,
    },
    {
        "key": "receipt_draft",
        "title": "Receipt draft",
        "domain": "finance",
        "risk": "propose",
        "status": "live",
        "accessory": "accounting.gl",
        "soft_wall": True,
        "sync": True,
    },
    {
        "key": "field_report_draft",
        "title": "Field report draft",
        "domain": "field",
        "risk": "propose",
        "status": "live",
        "accessory": "field.operations",
        "soft_wall": True,
        "sync": True,
    },
]

BUSINESS_NODES: list[dict[str, Any]] = [
    {
        "key": "cashflow_explain",
        "title": "Cashflow explain",
        "domain": "finance",
        "risk": "read",
        "status": "live",
        "accessory": "accounting.gl",
        "sync": True,
    },
    {
        "key": "debt_followup_propose",
        "title": "Debt follow-up propose",
        "domain": "finance",
        "risk": "outbound",
        "status": "live",
        "accessory": "accounting.gl",
        "soft_wall": True,
        "sync": True,
    },
    {
        "key": "supplier_match",
        "title": "Supplier match",
        "domain": "marketplace",
        "risk": "read",
        "status": "live",
        "accessory": "marketplace",
        "sync": True,
    },
    {
        "key": "project_risk_summary",
        "title": "Project risk summary",
        "domain": "projects",
        "risk": "read",
        "status": "live",
        "accessory": "drilling.projects",
        "sync": True,
    },
    {
        "key": "compliance_check",
        "title": "Compliance check",
        "domain": "compliance",
        "risk": "read",
        "status": "live",
        "accessory": "compliance.registry",
        "sync": True,
    },
    {
        "key": "tender_support",
        "title": "Tender support",
        "domain": "business",
        "risk": "propose",
        "status": "stub",
        "accessory": "contractor.crm",
        "soft_wall": True,
        "sync": True,
    },
    {
        "key": "training_recommend",
        "title": "Training recommend",
        "domain": "workforce",
        "risk": "propose",
        "status": "live",
        "accessory": "workforce",
        "sync": True,
    },
    {
        "key": "association_digest",
        "title": "Association digest",
        "domain": "association",
        "risk": "read",
        "status": "live",
        "accessory": "association.ams",
        "sync": True,
        "national": True,
    },
]

NATIONAL_NODES: list[dict[str, Any]] = [
    {
        "key": "national_aggregate_summary",
        "title": "National aggregate summary",
        "domain": "national",
        "risk": "read",
        "status": "live",
        "accessory": "national.intelligence",
        "sync": True,
        "national": True,
        "min_cell_threshold": 5,
    },
    {
        "key": "bdag_intelligence_query",
        "title": "BDAG intelligence query",
        "domain": "national",
        "risk": "read",
        "status": "live",
        "accessory": "national.intelligence",
        "sync": True,
        "national": True,
        "min_cell_threshold": 5,
    },
]

READ_NODES: list[dict[str, Any]] = [
    {"key": "read_organisation", "title": "Read organisation", "domain": "reads", "risk": "read", "status": "live", "accessory": "core.auth"},
    {"key": "read_stakeholder_context", "title": "Read stakeholder context", "domain": "reads", "risk": "read", "status": "live", "accessory": "core.auth"},
    {"key": "read_project", "title": "Read project", "domain": "reads", "risk": "read", "status": "live", "accessory": "drilling.projects"},
    {"key": "read_borehole", "title": "Read borehole", "domain": "reads", "risk": "read", "status": "live", "accessory": "field.operations"},
    {"key": "read_drilling_report", "title": "Read drilling report", "domain": "reads", "risk": "read", "status": "live", "accessory": "field.operations"},
    {"key": "read_rig", "title": "Read rig", "domain": "reads", "risk": "read", "status": "live", "accessory": "fleet.maintenance"},
    {"key": "read_stock", "title": "Read stock", "domain": "reads", "risk": "read", "status": "live", "accessory": "inventory.pos"},
    {"key": "read_workforce", "title": "Read workforce", "domain": "reads", "risk": "read", "status": "live", "accessory": "workforce"},
    {"key": "read_quote", "title": "Read quote", "domain": "reads", "risk": "read", "status": "live", "accessory": "quotes.location"},
    {"key": "read_payment", "title": "Read payment", "domain": "reads", "risk": "read", "status": "live", "accessory": "accounting.gl"},
    {"key": "read_compliance", "title": "Read compliance", "domain": "reads", "risk": "read", "status": "live", "accessory": "compliance.registry"},
    {"key": "read_marketplace", "title": "Read marketplace", "domain": "reads", "risk": "read", "status": "live", "accessory": "marketplace"},
    {"key": "read_association", "title": "Read association", "domain": "reads", "risk": "read", "status": "live", "accessory": "association.ams"},
]


def all_nodes() -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    for group in (FIELD_NODES, BUSINESS_NODES, NATIONAL_NODES, READ_NODES):
        for node in group:
            entry = dict(node)
            entry.setdefault("version", "1.0.0")
            entry.setdefault("product", "abbis")
            entry.setdefault("soft_wall", False)
            entry.setdefault("sync", True)
            entry.setdefault("idempotent", False)
            entry.setdefault("national", False)
            entry["required_grants"] = (f"node:{entry['key']}",)
            nodes[entry["key"]] = entry
    return nodes


def nodes_for_stakeholder(stakeholder: str, accessories: set[str] | frozenset[str]) -> list[str]:
    from isolation import STAKEHOLDER_ACCESSORIES

    allowed = set(accessories) or set(STAKEHOLDER_ACCESSORIES.get(stakeholder, frozenset()))
    out: list[str] = []
    for key, node in all_nodes().items():
        accessory = node.get("accessory")
        if accessory and accessory not in allowed and stakeholder not in {"platform", "S14"}:
            if node.get("national") and stakeholder not in {"S01", "S14"}:
                continue
            if accessory not in allowed:
                continue
        if node.get("national") and stakeholder not in {"S01", "S14", "platform"}:
            continue
        out.append(key)
    return sorted(out)
