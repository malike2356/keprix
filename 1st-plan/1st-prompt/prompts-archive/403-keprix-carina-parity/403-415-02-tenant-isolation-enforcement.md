# Prompt 405 / 02: Tenant isolation enforcement

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 404 / 01  
Blocks: 406, 410  
Severity: CRITICAL  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Foundation without enforcement is theater. Stores and APIs that are workspace-scoped must reject cross-tenant reads/writes.

## Goal

Enforce tenant scoping on high-risk surfaces first: workspace calendar/events, viCal store, contacts, vault metadata pointers, and agent tool user_id resolution. Soft-fail with IsolationError-style responses.

## Must-haves

1. Shared helper `assert_tenant_owns(resource)` / query filter.
2. Apply to: vical store, calendar store, contacts store list/get, capability mesh audit (optional tag).
3. Middleware/tests that simulate cross-tenant token and expect 403/404.
4. Ops doc: how CE single-tenant stays compatible (default tenant).

## Acceptance

- [x] Cross-tenant booking/event/contact fetch fails closed.
- [x] Default single-tenant CE path still works without config drama.
