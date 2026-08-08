"""Register ABBIS tools on the pack registry."""

from __future__ import annotations

from typing import Any

from nodes.catalog import all_nodes
from tools import handlers
from tools.registry import registry

_MAP = {
    "pipe_count_calculate": handlers.pipe_count_calculate_handler,
    "pump_yield_calculate": handlers.pump_yield_calculate_handler,
    "quote_calculate": handlers.quote_calculate_handler,
    "rod_depth_calculate": handlers.rod_depth_calculate_handler,
    "pe_hose_calculate": handlers.pe_hose_calculate_handler,
    "pump_hp_calculate": handlers.pump_hp_calculate_handler,
    "job_brief": handlers.job_brief_handler,
    "drilling_log_assist": handlers.drilling_log_assist_handler,
    "stock_usage_propose": handlers.stock_usage_propose_handler,
    "rpm_maintenance_assess": handlers.rpm_maintenance_assess_handler,
    "receipt_draft": handlers.receipt_draft_handler,
    "field_report_draft": handlers.field_report_draft_handler,
    "cashflow_explain": handlers.cashflow_explain_handler,
    "debt_followup_propose": handlers.debt_followup_propose_handler,
    "supplier_match": handlers.supplier_match_handler,
    "project_risk_summary": handlers.project_risk_summary_handler,
    "compliance_check": handlers.compliance_check_handler,
    "tender_support": handlers.tender_support_handler,
    "training_recommend": handlers.training_recommend_handler,
    "association_digest": handlers.association_digest_handler,
    "national_aggregate_summary": handlers.national_aggregate_summary_handler,
    "bdag_intelligence_query": handlers.national_aggregate_summary_handler,
}

for name, handler in _MAP.items():
    registry.register(name, handler)


def _read_handler(node_key: str):
    def _handler(args: dict[str, Any], **_kwargs: Any) -> str:
        return handlers.read_stub_handler(node_key, args)

    return _handler


for key in all_nodes():
    if key.startswith("read_") and key not in _MAP:
        registry.register(key, _read_handler(key))
