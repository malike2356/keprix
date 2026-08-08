# Prompt 449 / 20: Domain pack docs, self-knowledge, operator runbook

**Status: COMPLETED 2026-08-08** (pending parent archive; do not leave orphan)

## What was built

- `docs/features/agentic-crm.md` runbook + Soft Wall honesty + `/crm/*` sitemap
- Pack docs under `docs/features/crm-packs/` + `generic.yaml` pack
- Self-knowledge parity snippets for objects/routes/tools/packs/compliance
- Self-knowledge indexer paths for CRM enroll retrieval
- Gap map statuses updated for 449+

**Series:** 429-450  
**Depends on:** 440, 441, 447  
**Blocks:** 450  
**Writing style:** plain ASCII only.

## Goal

Operators and the agent know how to run the funnel per vertical.

## Must-haves

1. Docs: `docs/features/agentic-crm.md`, pack docs under `docs/features/crm-packs/`.
2. Runbook: discovery -> enrich -> Soft Wall -> enroll -> nurture -> book.
3. Channel prompt cookbook (Telegram + web examples).
4. Self-knowledge index snippets for CRM tools and packs.
5. Architecture gap map updated to DONE/partial per prompt.
6. Marketing-facing honesty: what is automated vs Soft Wall.
7. Sitemap of Must `/crm/*` routes matching 466 IA; runbook steps cite routes
   not only API/tool names.

## Acceptance

- [ ] `keprix memory search-self "crm enroll"` returns useful chunk after index
- [ ] Runbook steps match shipped UI routes
- [ ] Pack docs list enabled vs stub adapters
- [ ] Feature doc includes operator console section (jobs, inbox, deliverability)

## Done When

450 can sign off against written behaviour.
