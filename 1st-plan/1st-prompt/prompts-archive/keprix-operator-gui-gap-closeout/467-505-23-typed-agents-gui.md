# Prompt 490 / 23: Typed agents inventory GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/typed-agents` inventory + schema export


**Depends on:** 467, `/api/typed-agents`
**Blocks:** 505

## Goal

List/export/run typed agent schemas for operators (not SDK-only).

## Must-haves

1. Route `/admin/typed-agents` or `/agent-studio/typed`.
2. Inventory table; schema view; Soft Wall run sample.
3. Export schema JSON.
4. Nav + docs; tests.

## Acceptance

- [x] Operator lists typed agents and views schema in GUI
- [x] Sample run Soft Wall gated if side effects

## Done When

Typed agents are discoverable in workspace.
