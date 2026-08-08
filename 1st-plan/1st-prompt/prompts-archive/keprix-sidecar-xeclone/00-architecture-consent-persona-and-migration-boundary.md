# Prompt XCS-00: Xeclone architecture, consent, persona, and migration boundary

**Status: COMPLETED 2026-08-08**
**Depends on:** xeclone migration plan, shared contract
**Blocks:** XCS-01 through XCS-05

## Goal

Lock an owner-consented digital-clone boundary and staged migration from current
Carina/Aiva execution to Keprix without two conflicting personas or memories.

## Must-haves

1. Inventory persona files, digital footprint, relationships, text/audio/image/
   video assets, n8n workflows, Carina worker, OAuth channels, approvals, Scout,
   storage, providers and current migration gaps.
2. Define owner/subject consent ledger per asset and capability: ingest, index,
   train, generate, transform, upload to provider, publish, private message, retain,
   export and delete. Consent is versioned, revocable and checked at execution.
3. Define responsibilities: xeclone owns identity assets, consent, product UX,
   channel accounts and approvals; Keprix owns persona runtime, scoped RAG,
   multimodal jobs and playbooks; Carina owns Phase 1 paths until cut over.
4. Establish one canonical persona source and build artifact. Carina and Keprix
   consume pinned versions during dual-run; no manual prompt drift.
5. Threat-model deepfake misuse, private-message impersonation, biometric theft,
   relationship leakage, voice replay fraud, prompt injection in personal archives,
   poisoned training data, cross-tenant memory and unauthorised publishing.
6. Risk classes: private draft, owner conversation, public content draft, voice,
   likeness image, talking-head video, account publish, private reply and autonomous
   engagement. Publishing/private reply are always separately gated initially.
7. Define disclosure, watermark, provenance/C2PA where available, content labels,
   provider-upload policy, deletion and incident kill switch.
8. Preserve Wave 0: do not change the live Carina/Aiva path from this prompt.

## Acceptance

- [ ] Every asset and action has a consent purpose and controller
- [ ] One persona version maps across Carina and Keprix
- [ ] Migration waves have entry, exit, rollback and ownership
- [ ] No live runtime changes occur during architecture work

## What was built

- `docs/architecture.md`, threat model, consent ledger, persona pin `ilaud@0.1.0`
- Migration waves documented; Wave 0 preserves Carina live path

