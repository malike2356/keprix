# Prompt 500 / 33: Hot-cache and workspace ops GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/workspace-ops` hot-cache status/refresh Soft Wall flush


**Depends on:** 467
**Blocks:** 505

## Goal

Expose hot-cache flush/status and related workspace ops that today are API-only.

## Must-haves

1. Route `/admin/workspace-ops` or section under `/admin` / developer.
2. Hot-cache status + Soft Wall flush per workspace.
3. Link workspace templates / `/workspace/new` without duplicating that wizard.
4. Admin-only; audit; tests; docs.
5. Honest no-op if hot-cache disabled.

## Acceptance

- [x] Admin flushes hot-cache from GUI
- [x] Audit event recorded

## Done When

Occasional ops do not require curl.
