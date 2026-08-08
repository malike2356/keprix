# Keprix sidecar readiness for Xeclone and iLaud

**Status: COMPLETED 2026-08-08**
**Product:** Consent-governed multimodal digital clone
**Contract:** `../ref-keprix-product-sidecar-contract.md`

## Build order

1. `00-architecture-consent-persona-and-migration-boundary.md`
2. `01-domain-pack-multimodal-nodes-and-tools.md`
3. `02-carina-bridge-product-api-and-dual-run.md`
4. `03-provisioning-assets-vault-rag-and-models.md`
5. `04-approval-publishing-channels-and-scout-governance.md`
6. `05-evals-migration-cutover-rollback-and-signoff.md`

Carina/Aiva remains the Phase 1 runtime until migration gates pass. Keprix must
not impersonate, publish, send, train, or upload biometric assets without the
owner's explicit scope and the required approval.

## What was built

- Full `domain-packs/xeclone/` sidecar (port 3361)
- Docs, evals, CLI provision, sign-off READY local/staging
- Tests: 16 passed

