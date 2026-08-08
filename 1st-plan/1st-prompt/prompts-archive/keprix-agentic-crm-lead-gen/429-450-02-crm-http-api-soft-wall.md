# Prompt 431 / 02: CRM HTTP API + Soft Wall hooks

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 430  
**Blocks:** 432, 434, 435  
**Writing style:** plain ASCII only.

## What was built

- `/api/crm/*` router: leads, accounts, contacts, deals, lists/members, activities,
  enrichments, suppressions, jobs, outbox, merges, contactability, deliverability,
  kill-switches, Soft Wall approvals
- Soft Wall gates via `crm/soft_wall.py` (typed payload on Soft Wall approvals)
- Role caps, pagination/filters, idempotency keys, bulk delete preview
- Tests: `tests/crm/test_crm_routes.py` (4) + store suite green

## Goal

REST surface for CRM with Soft Wall approval hooks for risky writes.

## Must-haves

1. Router `/api/crm/*` (accounts, leads, contacts, deals, lists, activities,
   enrichments, suppressions, jobs, outbox, merges, contactability,
   deliverability/sender-readiness, kill-switches). Thin stubs OK until 466
   finishes UI if OpenAPI lists them honestly.
2. Auth: `get_current_user` session (same as calendar/viCal).
3. Soft Wall integration points (create approval items, do not auto-apply when gate on):
   - apply enrichment
   - approve list for enroll
   - stage jump to customer/paying
   - merge identity suggestion
   - kill switch off / budget raise
4. Pagination, filter by stage/source/pack/tag, search q=.
5. OpenAPI schemas honest.
6. Tests with TestClient.
7. Role checks for view/edit/approve/export/send, optimistic concurrency,
   idempotency keys, request limits, stable error codes, and audit correlation ids.
8. Bulk endpoints return preview/count first and use recoverable soft delete.
   Exports and analytics receive the same workspace isolation tests as CRUD.
9. Every Soft Wall-gated write returns approval id + deep-link hint for `/crm`
   Soft Wall panel and object detail.

## Acceptance

- [x] List/create/update/delete lead + list membership work
- [x] Soft Wall gate can block enroll until approved
- [x] 401 without session when auth enabled
- [x] Jobs/outbox/merges/contactability endpoints exist or documented stubs for 466

## Done When

UI and agent tools can call stable routes.
