# Prompt 430 / 01: CRM domain model + store + isolation

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 429  
**Blocks:** 431, 433, 436  
**Writing style:** plain ASCII only.

## What was built

- Package `src/keprix/crm/`: models, schema, store, identity resolver, bootstrap
- Workspace-scoped SQLite CRM (Soft Wall pattern) with soft delete + versions
- Objects: Account, Lead, Contact, Deal, Activity, List, ListMembership,
  EnrichmentJob, ConsentRecord, SuppressionEntry, plus DiscoveryJob, OutboxRecord,
  MergeSuggestion, ContactabilityDecision, SenderReadiness, KillSwitchState,
  field provenance, source records, merge history, idempotency
- Identity resolution: exact upsert keys; fuzzy -> merge suggestions only
- API startup bootstrap via `ensure_crm_tables` in `api/server.py`
- Tests: `tests/crm/test_crm_store.py` (7 passed)

## Goal

Persist workspace-scoped CRM objects with isolation and audit fields.

## Must-haves

1. Store (SQLite/JSON or Postgres-backed consistent with Soft Wall/contacts pattern) under `src/keprix/crm/`.
2. Models: Account, Lead, Contact, Deal, Activity, List, ListMembership, EnrichmentJob, ConsentRecord, SuppressionEntry.
3. Fields must include stage, source, domain_pack, emails/phones, company identifiers (CH number optional), scores, tags, assigned_agent, last_touch_at.
4. Tenant/workspace isolation on every query (see `docs/TENANT-ISOLATION.md` if present; else Soft Wall pattern).
5. Idempotent upsert keys: email+workspace, CH number+workspace, external_source_id.
6. Migration / bootstrap on API startup.
7. Unit tests for isolation and upsert.
8. Central workspace-scoped repository, optimistic versions, soft delete,
   field provenance, source records, merge history, and reversible merge suggestions.
9. Identity resolution service with exact verified keys. Fuzzy matching must
   produce review suggestions and must never merge consent between people.
10. Transactional outbox/inbox primitives and idempotency records for later
    discovery, send, reply, and booking integrations.
11. Models/APIs must support later GUI surfaces (466): DiscoveryJob history,
    OutboxRecord, MergeSuggestion, ContactabilityDecision, SenderReadiness,
    KillSwitchState. Prefer first-class types over opaque JSON blobs.

## Acceptance

- [x] CRUD via Python API
- [x] Cross-workspace read fails closed
- [x] pytest green
- [x] Provenance and merge suggestion shapes ready for `/crm/merges` UI

## Done When

431 can expose HTTP without inventing schema.
