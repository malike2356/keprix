# Prompt 441 / 12: Health and social care vertical pack stub

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 436, 433  
**Blocks:** 449  
**Writing style:** plain ASCII only.

## What was built

- src/keprix/discovery/ adapters + Soft Wall materialize
- /crm/discover + /crm/jobs UI
- tests/discovery


## Goal

Health / social care pack with schemas and adapter stubs for sector directories (CQC, local authority lists, etc.) without shipping unsafe scrape.

## Must-haves

1. Pack manifest: sheet types `clinic_referrals`, `care_providers`, `practitioners`.
2. Column presets: organisation, CQC id, services, region, contact, capacity metrics.
3. Adapter stubs: `cqc_api` (if public API), `health_csv`, `directory_web` reuse.
4. Extra consent sensitivity: mark health outreach as high-risk Soft Wall always-on.
5. Docs: sector compliance notes (UK care marketing rules high level; not legal advice).
6. Tests: pack loads; high-risk gate forced.

## Acceptance

- [x] User can preprocess a care-provider CSV into CRM List
- [x] Enroll requires Soft Wall even if workspace loosened other gates
- [x] Stub adapters honest when API missing

## Done When

Non-property verticals are first-class in the pack system.
