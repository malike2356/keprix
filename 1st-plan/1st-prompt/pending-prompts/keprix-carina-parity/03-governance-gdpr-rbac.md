# Prompt 406 / 03: Governance, GDPR hooks, RBAC depth

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 405 / 02  
Blocks: 407  
Severity: HIGH  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina has GDPR module, compliance audits, security findings. Keprix has kill relay / workspace lock stubs and roles in nav filtering, but not a coherent governance product.

## Goal

Ship a minimal governance package: roles matrix documented + enforced on admin APIs, data-export/delete request workflow stubs with audit log, retention policy config.

## Baseline

Existing: `governance/`, feature flags, ui_contract roles, Channel Shield. Extend; do not invent a second RBAC.

## Must-haves

1. `docs/features/governance.md` role x capability matrix.
2. Audit event store for governance actions (export/delete/role change).
3. API endpoints for DSAR export request + deletion request (operator).
4. Tests for unauthorized admin route denial.

## Acceptance

- [x] Viewer cannot hit admin governance mutations.
- [x] Export/delete requests leave an audit row.
