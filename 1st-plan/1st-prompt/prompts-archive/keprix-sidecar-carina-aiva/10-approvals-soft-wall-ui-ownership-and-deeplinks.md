# Prompt 526 / CAS-10: Approvals Soft Wall UI ownership and deeplinks

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 523
**Blocks:** 531
**Writing style:** plain ASCII only.

## Goal

Keep Soft Wall / approvals UX owned by Carina/Aiva product surfaces while Keprix
capabilities block and resume with approval evidence.

## Must-haves

1. Single Soft Wall bus (existing Soft Wall / outreach ops approvals). No parallel
   "Keprix approvals" product.
2. Invoke responses include `approval_id`, reason, and product deep link
   (`/crm`, Aiva Soft Wall, Carina approvals).
3. `POST .../approvals/{id}/decision` on northbound accepts product-signed
   decisions and resumes blocked nodes idempotently.
4. UI shows pending Keprix-originated gates beside existing gates.
5. Expiry and payload hash binding; material input change invalidates approval.
6. Tests: resume without approval denied; stale approval denied; approve then
   enroll succeeds once.

## Acceptance

- [ ] Operator never needs server logs to approve a blocked CRM/outreach action
- [ ] Double approve does not double-send
- [ ] Aiva and Carina deep links resolve to the correct product surface

## Done When

Soft Wall remains one operator story across engines.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
