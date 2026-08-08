# Prompt 492 / 25: Interfaces bind/dispatch GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/interfaces` bind + dispatch


**Depends on:** 467, `/api/interfaces`
**Blocks:** 505

## Goal

Thin admin GUI for channel interface binding and dispatch debug.

## Must-haves

1. Route `/admin/interfaces`.
2. Bind/list/unbind channel interfaces; dispatch dry-run.
3. Soft Wall for bind changes in production workspaces.
4. Nav + tests + docs.

## Acceptance

- [x] Admin binds interface from GUI
- [x] Dry-run shows dispatch target

## Done When

Interface ops are not developer-API-only.
