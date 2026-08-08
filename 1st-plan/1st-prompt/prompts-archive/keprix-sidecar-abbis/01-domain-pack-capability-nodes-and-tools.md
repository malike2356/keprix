# Prompt ABS-01: ABBIS domain pack, capability nodes, and tools

**Status: COMPLETED 2026-08-08**
**Depends on:** ABS-00
**Blocks:** ABS-02, ABS-04

## What was built

- domain-packs/abbis pack (manifest, schemas, glossary, playbooks)
- Deterministic calculators (pipe/pump/quote) from spec/07
- Field + business + national capability nodes and tool handlers


## Goal

Build `domain-packs/abbis/` from ABBIS manifests and canonical formulas.

## Must-haves

1. Pack manifest, stakeholder persona bindings, module registrations, glossary,
   schemas, tools, playbooks, localisation keys, RAG chunkers, policies and tests.
2. Common reads: organisation, stakeholder context, project/site, borehole,
   drilling report, rig, vehicle, stock, workforce, quote, invoice, payment,
   compliance, marketplace, association and approved aggregate views.
3. Field nodes: `job_brief`, `drilling_log_assist`, `pipe_count_calculate`,
   `pump_yield_calculate`, `quote_calculate`, `stock_usage_propose`,
   `rpm_maintenance_assess`, `receipt_draft`, `field_report_draft`.
4. Business nodes: `cashflow_explain`, `debt_followup_propose`,
   `supplier_match`, `project_risk_summary`, `compliance_check`,
   `tender_support`, `training_recommend`, `association_digest`.
5. National/BDAG nodes accept only authorised aggregate schemas and minimum cell
   thresholds. They cannot retrieve individual tenant or worker records.
6. Formulas call versioned deterministic ABBIS calculation services. LLM may
   explain inputs/results but cannot replace or alter canonical math.
7. Writes are proposal/action separated. Stock deduction, financial posting,
   worker payment, quote issue, customer message and marketplace action require
   product validation, entitlement and configured approval.
8. Every response localises through ABBIS, cites record ids/versions and labels
   observed, calculated, inferred and human-verified values.
9. No hardcoded Kari sample values, English-only copy, `KB` quote prefix or
   incorrect association/operator naming.

## Acceptance

- [x] Pack registers through the unified intelligence mesh
- [x] Stakeholder sees only entitled nodes and context
- [x] Formula fixtures exactly match ABBIS specifications
- [x] National tools cannot expose or infer a small tenant's records
