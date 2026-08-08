# Prompt 489 / 22: Code-agent sessions GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/code-agent` sessions list/detail/trace pause/resume
- Distinct from `/admin/coding`; nav synced


**Depends on:** 467, `/api/code-agent`
**Blocks:** 505

## Goal

Coding ladder exists; full code-agent session oversight does not.

## Must-haves

1. Route `/admin/code-agent` or `/coding/sessions`.
2. Session list/detail: status, repo scope, tool calls summary, Soft Wall stops.
3. Actions: cancel, open logs, Soft Wall continue.
4. Link from coding ladder.
5. Tests; isolation; no secret leakage in UI.
6. Nav sync.

## Acceptance

- [x] Operator monitors/cancels sessions from GUI
- [x] Deep link from ladder works

## Done When

Code-agent is not API-session-only.
