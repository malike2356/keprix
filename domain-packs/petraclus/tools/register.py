"""Register Petraclus tools on the pack registry."""

from __future__ import annotations

from nodes.catalog import all_nodes
from tools import handlers
from tools.registry import registry

_MAP = {
    "asset_get": handlers.asset_get_handler,
    "scan_get": handlers.scan_get_handler,
    "finding_get": handlers.finding_get_handler,
    "finding_search": handlers.finding_search_handler,
    "evidence_get_redacted": handlers.evidence_get_redacted_handler,
    "report_get": handlers.report_get_handler,
    "audit_get": handlers.audit_get_handler,
    "integration_health": handlers.integration_health_handler,
    "finding_explain": handlers.finding_explain_handler,
    "severity_review": handlers.severity_review_handler,
    "false_positive_propose": handlers.false_positive_propose_handler,
    "attack_path_summarise": handlers.attack_path_summarise_handler,
    "control_map": handlers.control_map_handler,
    "remediation_plan": handlers.remediation_plan_handler,
    "executive_summary": handlers.executive_summary_handler,
    "report_draft": handlers.report_draft_handler,
    "feed_item_assess": handlers.feed_item_assess_handler,
    "query_findings": handlers.query_findings_handler,
    "scan_plan_propose": handlers.scan_plan_propose_handler,
    "finding_triage_propose": handlers.finding_triage_propose_handler,
    "remediation_change_propose": handlers.remediation_change_propose_handler,
    "exception_propose": handlers.exception_propose_handler,
    "ticket_propose": handlers.ticket_propose_handler,
    "scan_start": handlers.scan_start_handler,
    "scan_cancel": handlers.scan_cancel_handler,
    "finding_update": handlers.finding_update_handler,
    "ticket_create": handlers.ticket_create_handler,
    "report_publish": handlers.report_publish_handler,
}

for name, handler in _MAP.items():
    registry.register(name, handler)

# Ensure every catalog node is registered
for key in all_nodes():
    if key not in _MAP:
        raise RuntimeError(f"missing_handler_for_node:{key}")
