# Prompt 439 / 10: Social discovery adapters (API-first)

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 436  
**Blocks:** 449  
**Writing style:** plain ASCII only.

## What was built

- src/keprix/discovery/ adapters + Soft Wall materialize
- /crm/discover + /crm/jobs UI
- tests/discovery


## Goal

Facebook, Instagram, TikTok, LinkedIn discovery via **official APIs / export files** first. Scrapers are Nice/Ultimate and must stay feature-flagged off by default.

## Must-haves

1. Adapter stubs: `linkedin_api`, `meta_graph`, `tiktok_api`, `social_csv_export`.
2. Health endpoints report configured vs missing credentials.
3. LeadCandidate mapping from public org pages / lead gen forms where API allows.
4. Docs: legal note that scraping those platforms often violates ToS; Keprix will not enable scrape by default.
5. Soft Wall for any connection OAuth.
6. Tests: unconfigured returns clear error; fake configured path maps fields.

## Nice (same prompt if small, else defer)

- LinkedIn Marketing API lead sync when owner provides app.

## Acceptance

- [x] Agent saying "scrape Instagram" gets honest refusal + API path guidance
- [x] CSV export from social ads can import via social_csv_export
- [x] Flags default off for any scrape experimental code

## Done When

Social is represented without shipping illegal bots.
