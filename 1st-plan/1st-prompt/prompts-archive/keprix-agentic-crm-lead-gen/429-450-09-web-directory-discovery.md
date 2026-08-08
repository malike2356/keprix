# Prompt 438 / 09: Web search / directory discovery adapter

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 436  
**Blocks:** 442  
**Writing style:** plain ASCII only.

## What was built

- src/keprix/discovery/ adapters + Soft Wall materialize
- /crm/discover + /crm/jobs UI
- tests/discovery


## Goal

Discover businesses from allowed web/search backends (SearxNG / configured search) into LeadCandidates.

## Must-haves

1. Adapter `web_directory` using existing SearxNG or search tools.
2. Query templates per domain pack ("plumbers in Manchester", "care homes in Kent").
3. Extract site title, url, snippet; optional homepage fetch for email/phone with egress allowlist and robots respect.
4. Soft Wall before bulk homepage fetch (cost + ToS).
5. Honest limits: max pages, max fetches/job.
6. Tests with mocked search results.

## Acceptance

- [x] Job returns candidates with source=web_directory
- [x] Fetch disabled by default until Soft Wall approve
- [x] No silent bypass of egress allowlist

## Done When

Generic verticals without CH still have a discovery path.
