# Prompt 502 / 35: Docs, runbooks, self-knowledge (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Glossary + fleet/improvement docs; inventory/signoff updated


**Depends on:** 501
**Blocks:** 505

## Goal

Operators and agent self-knowledge know where every newly surfaced GUI lives.

## Must-haves

1. Docs:
   - `docs/architecture/operator-gui-gap-inventory.md` (status DONE/partial)
   - Feature docs for Tool ACL, Soft Wall safety pages, sheet preprocess,
     discovery, fleet, companion, data plane/jobs/ML/export, platform admin pages
2. Runbook: "operator GUI map" with routes table.
3. Update mobile.md, data-planes.md, Soft Wall docs, settings.md.
4. Self-knowledge index snippets for new tools/routes.
5. Marketing honesty: what is GUI vs Soft Wall vs API.
6. Writing style: plain ASCII; run workspace style check if docs bulk-edited.

## Acceptance

- [x] `keprix memory search-self` finds Tool ACL / outbox / data plane chunks
      after index
- [x] Runbook routes match shipped nav

## Done When

503 can sign off against written behaviour.
