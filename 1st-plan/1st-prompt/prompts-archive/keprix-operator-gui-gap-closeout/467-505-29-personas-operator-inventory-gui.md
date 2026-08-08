# Prompt 496 / 29: Personas operator inventory GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/personas` inventory + skill packs


**Depends on:** 467, `/api/personas`
**Blocks:** 505

## Goal

Agent Studio picker is insufficient for operator inventory/status of Forge /
Warden / Sage / Beacon and peers.

## Must-haves

1. Route `/agent-studio/personas` or `/admin/personas`.
2. Inventory: name, status, routing hints, last used, health.
3. Detail: config summary (no secrets), Soft Wall enable/disable if supported.
4. Keep Studio picker; link "Manage personas".
5. Use existing personas API depth; do not reimplement runtime.
6. Nav + tests + docs.

## Acceptance

- [x] Operator sees all personas status from GUI
- [x] Studio picker still works

## Done When

Persona ops are not picker-only.
