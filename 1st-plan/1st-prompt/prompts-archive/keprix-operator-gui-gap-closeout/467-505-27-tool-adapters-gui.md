# Prompt 494 / 27: Tool adapters registry GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/tool-adapters` catalog + dry-run Soft Wall


**Depends on:** 467, `/api/tools/adapters`
**Blocks:** 505

## Goal

Enable/configure tool adapters from GUI.

## Must-haves

1. Route `/admin/tool-adapters` (distinct from `/admin/tools` mutation tools and
   `/admin/tool-acl`).
2. List adapters, health, enable/disable Soft Wall, config form (secrets via vault
   refs only).
3. Nav labels honest among tools / ACL / adapters.
4. Tests + docs.

## Acceptance

- [x] Operator enables adapter from GUI
- [x] Secrets never pasted into adapter row plaintext

## Done When

Adapter config is not API-only.
