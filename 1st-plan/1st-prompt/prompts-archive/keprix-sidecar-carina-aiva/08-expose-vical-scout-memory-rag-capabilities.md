# Prompt 524 / CAS-08: Expose viCal, Scout hooks, memory, and RAG capabilities

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 517, 522
**Blocks:** 527
**Writing style:** plain ASCII only.

## Goal

Expose booking, Scout governance hooks, memory, and RAG admin capabilities to
Carina/Aiva through the sidecar, without merging Scout OPS into Carina OPS.

## Must-haves

1. Nodes: vical.offer_booking, vical.list_slots, memory.search, memory.write
   (policy gated), rag.search, rag.ingest Soft Wall, scout.emit_sanitized_event,
   scout.request_control (audited, scoped).
2. Scout remains the governance console; Carina only sends sanitized telemetry and
   receives scoped control actions with audit.
3. Memory namespaces include product+workspace; no Clinicom bleed.
4. RAG ingest reuses Keprix/Carina existing upload policy (HTTPS only, pack scope).
5. Booking mutations Soft Wall or product confirmation as required by viCal rules.
6. Tests: scout control out of scope denied; memory cross-tenant deny; booking
   idempotency.

## Acceptance

- [ ] Booking offer creates product-visible artifact/approval, not orphan Keprix-only state
- [ ] Scout hooks never expose raw PII beyond allowlist
- [ ] RAG search is workspace scoped

## Done When

P1 non-CRM capabilities are invocable from the shell.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
