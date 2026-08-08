# Prompt 429 / 00: Overview, gap map, architecture lock

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450 Keprix agentic CRM + lead-gen  
**Depends on:** none  
**Blocks:** 430+  
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Architecture lock + gap map: `docs/architecture/agentic-crm-gap-map.md`
- Frozen object names, stage machine, Soft Wall gates, package paths
- Vertical pack interface + Must GUI IA (points at 466)
- Explicit non-goals and PECR/GDPR / ToS constraints
- Self-knowledge outline stub: `docs/self-knowledge/parity/agentic-crm-outline.md`

## Why this exists

Owner asked for a full agentic CRM / lead-gen / nurture / outreach funnel
driven by the Keprix agent with human-in-the-loop, domain-agnostic spreadsheet
preprocessing, discovery from many sources, Soft Wall execution, and channel
activation (especially Telegram). Adjacent modules exist; this series glues and
extends them.

## Goal

Lock architecture, inventory gaps, and acceptance criteria so later prompts do
not reinvent Soft Wall, contacts, or viCal.

## Must-haves

1. Publish gap map: Soft Wall, contacts, CH, opportunity, analytics import, viCal, Telegram, Carina spreadsheet worker (reference only).
2. Freeze object model names: Account, Lead, Contact, Deal, Activity, List, EnrichmentJob, ConsentRecord.
3. Freeze stage machine and Soft Wall gate list (see ref-429).
4. Decide package paths: prefer `src/keprix/crm/` + `src/keprix/sheet_preprocess/` + `src/keprix/discovery/`.
5. Document vertical pack interface (manifest + adapters).
6. Call out legal/ToS and PECR/GDPR as series constraints.
7. Update self-knowledge outline for later 449.
8. Lock Must GUI IA: every Soft Wall-gated Must capability must have a workspace
   route or Soft Wall panel; Telegram-only fails Must. Prompt **466** owns the
   operator console pack; foundation routes start in 432.

## Acceptance

- [x] Gap map committed under `docs/architecture/agentic-crm-gap-map.md`
- [x] Package paths agreed in that doc
- [x] Non-goals explicit (no Carina nest, no silent illegal scrape, no new Stripe prices)
- [x] Gap map lists Must GUI routes (or points at 466 IA table)

## Done When

Architecture doc exists; 430 can implement store without re-debating names.
