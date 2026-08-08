# Prompt 493 / 26: Intent schema admin GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/intent` schemas + extract smoke


**Depends on:** 467, `/api/intent`
**Blocks:** 505

## Goal

Register/edit domain intents without raw API for non-API users.

## Must-haves

1. Route `/admin/intents`.
2. CRUD Soft Wall for publish; draft vs active.
3. Validation errors honest; version history.
4. Nav + tests + docs.

## Acceptance

- [x] Admin registers intent from GUI
- [x] Publish Soft Wall gated

## Done When

Intent admin is workspace-operable.
