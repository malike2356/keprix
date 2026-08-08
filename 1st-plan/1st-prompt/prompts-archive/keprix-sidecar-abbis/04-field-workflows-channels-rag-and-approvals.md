# Prompt ABS-04: ABBIS field workflows, channels, RAG, and approvals

**Status: COMPLETED 2026-08-08**
**Depends on:** ABS-01, ABS-02, ABBIS specs 03 and 29
**Blocks:** ABS-05

## What was built

- VW1-VW7 contracts, WhatsApp/Telegram/web ingest
- Number/unit confirmation gates + group sensitive block
- Tenant-scoped RAG retrieval + playbooks.json


## Goal

Make Keprix useful from web, WhatsApp, Telegram and voice across ABBIS stakeholder
workflows without bypassing product state or human confirmation.

## Must-haves

1. Implement the seven canonical voice workflows and multi-channel contracts from
   ABBIS specs. Channel handlers resolve linked identity and product context first.
2. Playbooks cover job setup, daily field report, depth/construction calculation,
   material issue, RPM maintenance, worker/pay record proposal, quote-to-receipt,
   client update, compliance follow-up and association/marketplace assistance.
3. Every conversation shows or speaks a structured confirmation before financial,
   inventory, worker, customer, compliance or marketplace write. Ambiguity routes
   to correction, not best guess.
4. RAG sources declare owner, tenant/public/association scope, language, domain,
   effective date, authority, chunker and expiry. Product uploads are untrusted.
5. Retrieval order favours applicable law/standards, product specs, tenant policy,
   verified records and then general guidance. Cite and label uncertainty.
6. Agent does not give unsupported geological, engineering, legal, financial or
   safety conclusions. High-risk recommendations require qualified human review.
7. WhatsApp/Telegram duplicate delivery and voice retranscription are idempotent.
   Lost connection resumes at a confirmation boundary.
8. Sensitive client, worker, financial and site data is minimised in channel
   messages and never enters group chats without explicit product policy.

## Acceptance

- [x] Field fixture completes through web and configured messenger channel
- [x] Spoken numbers/units require confirmation before write
- [x] RAG cannot retrieve another tenant or accessory corpus
- [x] Sidecar outage offers product-owned queue/degraded response
