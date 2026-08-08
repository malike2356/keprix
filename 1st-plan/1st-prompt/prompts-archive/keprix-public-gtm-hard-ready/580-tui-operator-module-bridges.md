# Prompt 580: TUI operator module bridges (Nice)

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 579  
**Priority:** Nice  
**Blocks:** none (582 may note Nice incomplete)  
**Writing style:** plain ASCII only.

## Purpose

After honesty matrix, optionally bridge high-value GUI modules into TUI without
rewriting the entire Next.js surface.

## Scope (keep lean)

1. Add TUI commands or Command Center entries that deep-link or summarize:
   - Soft Wall status / kill switch (read + confirmed write if safe)
   - CRM enrich job list / open URL to `/crm/enrich`
   - Playbook list / open URL
2. Prefer API-backed summaries + "open in browser" over full TUI CRUD.
3. Tests for new CLI commands; no secret leakage in output.

## Out of scope

- Full CRM UI in Textual.
- Desktop Electron port of CRM.

## Acceptance

- [ ] At least two GUI-only areas gain TUI bridge entries.
- [ ] Matrix from 579 updated to partial where bridges land.
- [ ] Unit/CLI tests pass.

## Verification

```bash
keprix --help | head
# plus project test command for new CLI modules
```
