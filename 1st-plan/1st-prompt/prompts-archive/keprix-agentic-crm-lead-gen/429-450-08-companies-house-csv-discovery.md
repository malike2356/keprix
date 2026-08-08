# Prompt 437 / 08: Companies House + CSV discovery to List

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 436, 432  
**Blocks:** 442  
**Writing style:** plain ASCII only.

## What was built

- src/keprix/discovery/ adapters + Soft Wall materialize
- /crm/discover + /crm/jobs UI
- tests/discovery


## Goal

First production discovery paths: UK Companies House search and CSV upload into a CRM List for review.

## Must-haves

1. Adapter wrapping existing `integrations/companies_house` tools.
2. Query params: SIC/keywords, location, status, size limits.
3. Score hint from basic filters (active, has address, age).
4. CSV adapter: map columns via sheet_preprocess user_schema or auto.
5. UI: "Find companies" form on `/crm/discover` + Soft Wall create List.
6. Agent tool: `discovery_run(adapter=companies_house|csv, ...)`.
7. Dedupe against existing accounts/leads; ambiguous matches open `/crm/merges`
   Soft Wall (466), not silent overwrite.
8. Tests with mocked CH responses.
9. After run, deep-link to `/crm/jobs/{id}` and draft List; never leave operator
   with only a tool JSON response.

## Acceptance

- [x] Operator runs CH search -> List draft -> review in UI
- [x] CSV of 50 rows becomes List memberships
- [x] Duplicates merge or skip with report (merge Soft Wall when ambiguous)
- [x] Discover form reachable from CRM nav

## Done When

442 can enroll from a real List.
