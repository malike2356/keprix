# Prompt XCS-03: Xeclone provisioning, assets, vault, RAG, and model routing

**Status: COMPLETED 2026-08-08**
**Depends on:** XCS-02
**Blocks:** XCS-05

## Goal

Provision an isolated iLaud runtime whose identity assets and provider access are
traceable, revocable, encrypted and removable.

## Must-haves

1. `keprix product provision xeclone` installs pinned pack/persona, namespace,
   workload identity, consent policy, memory, job queues, provider routes and Scout.
2. Asset registry stores reference, owner/subject, media type, hash, capture source,
   consent/version, allowed uses/providers, quality, retention and deletion state.
   Raw biometrics stay in product-controlled encrypted storage where possible.
3. RAG ingestion uses allowlisted corpus manifests, sensitivity labels, relationship
   scopes, content hashes, dedupe, injection scanning, chunk provenance and expiry.
4. Vault separates product workload identity, channel OAuth, TTS/image/video
   providers and storage. Nodes receive narrow handles, never raw secret export.
5. Model router declares local/cloud, data use/retention, residency, modality,
   consent eligibility, cost and fallback. Provider training on inputs is disabled
   contractually/configurationally where required.
6. Async GPU/media jobs have quotas, cancellation, artifact expiry, checksums,
   content moderation, retry and dead-letter state.
7. Deprovision revokes tokens, cancels jobs, deletes indexes/cache/artifacts under
   policy and produces an auditable completion receipt.
8. Upgrade pins persona and pack separately; rollback restores both without losing
   consent revocations.

## Acceptance

- [ ] Clean provision and deprovision leave no usable identity secret
- [ ] RAG retrieval respects public/private/relationship boundaries
- [ ] Provider routing rejects consent-incompatible transfer
- [ ] Persona rollback never rolls back revocation records

## What was built

- Provision/deprovision receipts, asset registry, vault handles, RAG boundaries, model router
- `keprix product provision xeclone`

