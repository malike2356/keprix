# Prompt 491 / 24: Kernel plugins admin GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/kernel` plugins + traces


**Depends on:** 467, `/api/kernel`
**Blocks:** 505

## Goal

Plugin inventory/plan/invoke for admin debug.

## Must-haves

1. Route `/admin/kernel`.
2. List plugins, health, plan preview, Soft Wall invoke.
3. Admin-only; audit every invoke.
4. Nav + tests + docs.

## Acceptance

- [x] Admin inventories plugins from GUI
- [x] Invoke Soft Wall gated

## Done When

Kernel is inspectable without curl.
