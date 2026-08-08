# Prompt 480 / 13: Discovery run form + jobs GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/crm/discover` + `/crm/jobs` (+ job detail) live
- Nav: crm-discover, crm-jobs; CrmTabNav Discover/Jobs
- Soft Wall materialize from jobs detail; frontend smoke tests


**Depends on:** 479, 472, 473
**Blocks:** 505
**Aligns with:** CRM 437/466

## Goal

Operators run discovery and manage jobs without API tools.

## Must-haves

1. `/crm/discover`: form for CH/CSV (+ stub adapters disabled with reason).
2. `/crm/jobs`: history, cancel, retry dead-letter, Soft Wall materialize, open
   list draft, cost estimate.
3. Ambiguous matches open merges Soft Wall (473).
4. Nav entries; Soft Wall deep links.
5. Agent `discovery_run` returns GUI deep links.
6. Frontend smoke + empty/failed states.
7. Docs in agentic CRM / discovery feature doc.

## Acceptance

- [x] CH search -> Soft Wall list draft from GUI
- [x] Jobs cancel/retry from GUI
- [x] Discover reachable from nav

## Done When

Discovery is operator-usable.
