# Prompt PTS-01: Petraclus pack, capability nodes, and tools

## What was built

- `domain-packs/petraclus/` with 28 capability nodes (read/analysis/proposal/action)
- tools/{registry,handlers,register,safety}.py; no shell/nmap/exploit nodes
- Prompt-injection and target-grant guards


**Status: COMPLETED 2026-08-08**
**Depends on:** PTS-00
**Blocks:** PTS-02, PTS-04

## Goal

Build `domain-packs/petraclus/` with discoverable, schema-validated nodes that
explain and assist security work while preserving target and action controls.

## Must-haves

1. Manifest, compatibility, schemas, glossary, prompts, policies, playbooks,
   migrations, handlers, registry and tests following Keprix pack conventions.
2. Read nodes: `asset_get`, `scan_get`, `finding_get`, `finding_search`,
   `evidence_get_redacted`, `report_get`, `audit_get`, `integration_health`.
3. Analysis nodes: `finding_explain`, `severity_review`, `false_positive_propose`,
   `attack_path_summarise`, `control_map`, `remediation_plan`, `executive_summary`,
   `report_draft`, `feed_item_assess`, `query_findings`.
4. Proposal nodes: `scan_plan_propose`, `finding_triage_propose`,
   `remediation_change_propose`, `exception_propose`, `ticket_propose`.
5. Action nodes are separate: `scan_start`, `scan_cancel`, `finding_update`,
   `ticket_create`, `report_publish`. Each declares target grant, licence,
   approval, idempotency, sandbox and product validation requirements.
6. Do not ship generic shell, arbitrary HTTP, free-form nmap flags, exploit-run,
   credential-read, unrestricted file-read or remediation-execute nodes.
7. Treat all targets, banners, source code, findings and feed text as untrusted.
   Delimit data, detect instructions, constrain outputs and recheck policies.
8. Results cite asset/finding/evidence ids and distinguish observed scanner fact,
   feed data, model inference and human verification.
9. Node health reports dependencies such as scanner, feed, model and product API,
   plus live/degraded/disabled status and safe fallback.
10. Tools answer through plain language but retain CVE/CWE/CVSS/control references
    exactly. Models cannot silently change scanner severity or verified state.

## Acceptance

- [x] Capability discovery exposes stable schemas and risk classes
- [x] Read-only role cannot invoke mutations through playbook composition
- [x] Prompt-injected finding text cannot trigger a tool
- [x] Active scan node fails without a valid exact target grant
