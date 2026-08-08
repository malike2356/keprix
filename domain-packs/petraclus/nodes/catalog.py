"""Petraclus capability node catalog for the product sidecar."""

from __future__ import annotations

from typing import Any

EDITION_RANK = {"community": 0, "pro": 1, "team": 2}

READ_NODES: list[dict[str, Any]] = [
    {"key": "asset_get", "title": "Asset get", "domain": "reads", "risk": "read", "edition_min": "community"},
    {"key": "scan_get", "title": "Scan get", "domain": "reads", "risk": "read", "edition_min": "community"},
    {"key": "finding_get", "title": "Finding get", "domain": "reads", "risk": "read", "edition_min": "community"},
    {"key": "finding_search", "title": "Finding search", "domain": "reads", "risk": "read", "edition_min": "community"},
    {"key": "evidence_get_redacted", "title": "Evidence get redacted", "domain": "reads", "risk": "read", "edition_min": "community"},
    {"key": "report_get", "title": "Report get", "domain": "reads", "risk": "read", "edition_min": "community"},
    {"key": "audit_get", "title": "Audit get", "domain": "reads", "risk": "read", "edition_min": "pro"},
    {"key": "integration_health", "title": "Integration health", "domain": "reads", "risk": "read", "edition_min": "community"},
]

ANALYSIS_NODES: list[dict[str, Any]] = [
    {"key": "finding_explain", "title": "Finding explain", "domain": "analysis", "risk": "passive_enrich", "edition_min": "community"},
    {"key": "severity_review", "title": "Severity review", "domain": "analysis", "risk": "passive_enrich", "edition_min": "community"},
    {"key": "false_positive_propose", "title": "False positive propose", "domain": "analysis", "risk": "propose", "soft_wall": True, "edition_min": "community"},
    {"key": "attack_path_summarise", "title": "Attack path summarise", "domain": "analysis", "risk": "passive_enrich", "edition_min": "pro"},
    {"key": "control_map", "title": "Control map", "domain": "analysis", "risk": "passive_enrich", "edition_min": "pro"},
    {"key": "remediation_plan", "title": "Remediation plan", "domain": "analysis", "risk": "propose", "soft_wall": True, "edition_min": "pro"},
    {"key": "executive_summary", "title": "Executive summary", "domain": "analysis", "risk": "passive_enrich", "edition_min": "pro"},
    {"key": "report_draft", "title": "Report draft", "domain": "analysis", "risk": "propose", "soft_wall": True, "edition_min": "pro"},
    {"key": "feed_item_assess", "title": "Feed item assess", "domain": "analysis", "risk": "passive_enrich", "edition_min": "pro"},
    {"key": "query_findings", "title": "Query findings", "domain": "analysis", "risk": "passive_enrich", "edition_min": "team"},
]

PROPOSAL_NODES: list[dict[str, Any]] = [
    {"key": "scan_plan_propose", "title": "Scan plan propose", "domain": "proposal", "risk": "propose", "soft_wall": True, "requires_target_grant": True, "edition_min": "community"},
    {"key": "finding_triage_propose", "title": "Finding triage propose", "domain": "proposal", "risk": "propose", "soft_wall": True, "edition_min": "community"},
    {"key": "remediation_change_propose", "title": "Remediation change propose", "domain": "proposal", "risk": "propose", "soft_wall": True, "edition_min": "pro"},
    {"key": "exception_propose", "title": "Exception propose", "domain": "proposal", "risk": "propose", "soft_wall": True, "edition_min": "pro"},
    {"key": "ticket_propose", "title": "Ticket propose", "domain": "proposal", "risk": "propose", "soft_wall": True, "edition_min": "pro"},
]

ACTION_NODES: list[dict[str, Any]] = [
    {
        "key": "scan_start",
        "title": "Scan start",
        "domain": "action",
        "risk": "active_scan",
        "soft_wall": True,
        "requires_target_grant": True,
        "requires_approval": True,
        "edition_min": "community",
        "sync": False,
    },
    {
        "key": "scan_cancel",
        "title": "Scan cancel",
        "domain": "action",
        "risk": "mutate",
        "soft_wall": True,
        "requires_approval": True,
        "edition_min": "community",
    },
    {
        "key": "finding_update",
        "title": "Finding update",
        "domain": "action",
        "risk": "mutate",
        "soft_wall": True,
        "requires_approval": True,
        "edition_min": "community",
    },
    {
        "key": "ticket_create",
        "title": "Ticket create",
        "domain": "action",
        "risk": "outbound",
        "soft_wall": True,
        "requires_approval": True,
        "edition_min": "pro",
    },
    {
        "key": "report_publish",
        "title": "Report publish",
        "domain": "action",
        "risk": "mutate",
        "soft_wall": True,
        "requires_approval": True,
        "edition_min": "pro",
    },
]

FORBIDDEN_NODES = frozenset(
    {
        "shell",
        "arbitrary_http",
        "nmap_freeform",
        "exploit_run",
        "credential_read",
        "unrestricted_file_read",
        "remediation_execute",
    }
)

MUTATE_RISKS = frozenset(
    {
        "active_scan",
        "credentialed_scan",
        "mutate",
        "outbound",
        "destructive",
        "high_risk",
    }
)


def all_nodes() -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    for group in (READ_NODES, ANALYSIS_NODES, PROPOSAL_NODES, ACTION_NODES):
        for node in group:
            entry = dict(node)
            entry.setdefault("version", "1.0.0")
            entry.setdefault("product", "petraclus")
            entry.setdefault("status", "live")
            entry.setdefault("soft_wall", False)
            entry.setdefault("sync", True)
            entry.setdefault("requires_target_grant", False)
            entry.setdefault("requires_approval", False)
            entry.setdefault("edition_min", "community")
            entry["required_grants"] = (f"node:{entry['key']}",)
            if entry["risk"] in MUTATE_RISKS or entry["domain"] == "action":
                entry["required_grants"] = (f"node:{entry['key']}", "mutate")
            nodes[entry["key"]] = entry
    return nodes


def edition_allows(workspace_edition: str, edition_min: str) -> bool:
    return EDITION_RANK.get(workspace_edition, -1) >= EDITION_RANK.get(edition_min, 99)


def is_action_node(node_key: str) -> bool:
    node = all_nodes().get(node_key) or {}
    return node.get("domain") == "action" or node.get("risk") in MUTATE_RISKS
