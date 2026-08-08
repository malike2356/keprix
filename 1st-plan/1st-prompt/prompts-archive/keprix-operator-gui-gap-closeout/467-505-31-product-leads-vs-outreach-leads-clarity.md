# Prompt 498 / 31: Product leads vs Soft Wall leads UX clarity (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/leads` rewired to product signups `/api/leads`
- Cross-links + glossary


**Depends on:** 467
**Blocks:** 505

## Goal

`/leads` (product_leads) and `/outreach/leads` confuse operators.

## Must-haves

1. Rename labels (not necessarily routes): e.g. "Product signups" vs "Outreach
   leads" / "Soft Wall leads".
2. Cross-links and empty-state copy explaining difference.
3. When CRM `/crm/leads` exists, third label "CRM leads" with mesh links.
4. Nav group placement honest.
5. Docs glossary.
6. No data merge between systems in this prompt.

## Acceptance

- [x] Nav/page titles make system boundary obvious
- [x] Empty states point to the correct sibling

## Done When

Operators stop using the wrong leads UI.
