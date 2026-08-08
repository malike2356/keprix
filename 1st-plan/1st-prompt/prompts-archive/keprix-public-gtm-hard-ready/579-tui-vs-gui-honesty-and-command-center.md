# Prompt 579: TUI vs GUI honesty and Command Center scope

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570, 571  
**Blocks:** 580, 582  
**Writing style:** plain ASCII only.

## Purpose

Owner asked if the terminal is updated to match modules/features in Keprix.
Honest answer today: **TUI is not feature-complete vs web GUI** (CRM, Soft Wall
operator surfaces, etc.). Hard GTM must stop implying Hermes-class TUI covers
the whole product.

## Tasks

1. Produce `docs/architecture/tui-vs-gui-surface-matrix.md`:
   columns: feature area | GUI route | TUI command/screen | status
   (full / partial / GUI-only / planned).
2. Update TUI help / getting-started to point operators at web UI for GUI-only.
3. Command Center / operator docs: clarify TUI role (chat, tools, setup, status)
   vs Next.js workspace modules.
4. Marketing/docs: remove or rewrite any "full product in terminal" claims.

## Acceptance

- [ ] Matrix checked into docs.
- [ ] At least CRM Enrich / Soft Wall / Playbooks marked accurately.
- [ ] Stranger install path still ends in `keprix tui` for core agent use without
      claiming CRM parity.

## Verification

```bash
test -f docs/architecture/tui-vs-gui-surface-matrix.md
rg -n 'full product in (the )?terminal|everything in TUI' docs README.md || true
```
