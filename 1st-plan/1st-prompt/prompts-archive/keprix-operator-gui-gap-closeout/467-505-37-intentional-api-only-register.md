# Prompt 504 / 37: Intentional API-only / agent-only register (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Intentional non-GUI register in operator-gui-gap-inventory.md


**Depends on:** 467
**Blocks:** 505

## Goal

Leave nothing ambiguous: document surfaces that are **intentionally** without
full workspace GUI (slash/TUI, public `/v1`, Carina/Scout bridges, auth handoff,
health scrape, CLI auto-config, etc.) so future audits do not re-open false gaps.

## Must-haves

1. Section in `docs/architecture/operator-gui-gap-inventory.md`: Intentional
   non-GUI register with rationale (agent/TUI/integration/infra).
2. gui_catalog marks these `cli_api` or `integration` explicitly (not
   `missing_gui`).
3. Owner-approved list; do not hide real gaps here.
4. Cross-check against Critical/High Must list: none may be moved here without
   owner written approval in the doc.

## Acceptance

- [x] Register committed
- [x] No Critical/High item classified intentional without owner note
- [x] Catalog statuses match register

## Done When

False-positive GUI gap reports stop.
