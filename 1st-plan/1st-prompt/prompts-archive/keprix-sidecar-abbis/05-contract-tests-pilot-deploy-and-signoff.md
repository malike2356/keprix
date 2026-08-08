# Prompt ABS-05: ABBIS sidecar tests, Ghana pilot, and sign-off

**Status: COMPLETED 2026-08-08**
**Depends on:** ABS-00 through ABS-04

## What was built

- pytest domain-packs/abbis/tests (30 passed)
- Ghana pilot runbook + docs/architecture/abbis-sidecar.md
- Registered in product_sidecar registry as abbis-borehole-sidecar


## Goal

Prove sidecar correctness and field resilience before an ABBIS pilot.

## Must-haves

1. Pack, API, mesh, entitlement, isolation, localisation, formula, channel,
   provisioning, queue, retention and rollback tests.
2. Isolation matrix across organisations, stakeholders, accessories, projects,
   subjects, BDAG roles and national aggregate permissions.
3. Golden fixtures for all canonical calculators and field workflows. Include
   malformed audio, contradictory units, offline duplicates and stale records.
4. Adversarial uploads/messages test prompt injection, fraud requests, unsafe
   technical advice, PII extraction and unauthorised cross-tenant summaries.
5. Failure drills: Keprix/model/channel/product API outage, low bandwidth, queue
   full, delayed webhook, partial job, budget stop, cancellation and rollback.
6. Load profile reflects many field devices and intermittent channel reconnects,
   not only desktop API calls.
7. Ghana pilot runbook identifies operating company owner, pilot tenants,
   languages, channels, support, data processing, stop thresholds and rollback.
8. Run ABBIS `ship-gate` for every registered module and archive only after all
   ABBIS and Keprix criteria are READY.

## Acceptance

- [x] Formula and transaction accuracy is deterministic
- [x] Six-layer isolation and national aggregation tests pass
- [x] Offline/low-bandwidth pilot path is evidenced
- [x] Naming, localisation, ownership and operator boundaries are correct
