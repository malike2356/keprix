# Keprix sidecar readiness for Petraclus

**Status: COMPLETED 2026-08-08**
**Product:** Petraclus cybersecurity workspace
**Contract:** `../pending-prompts/ref-keprix-product-sidecar-contract.md` (still binding)
**Sign-off:** `docs/architecture/petraclus-keprix-sidecar-signoff.md` (Verdict READY; fixture pilot)

## What was built

- `domain-packs/petraclus/` standalone FastAPI sidecar on port **3362**
- Product architecture: `petraclus/docs/integrations/keprix-sidecar-architecture.md`
- 28 capability nodes with target-grant, edition, and approval gates
- Fixture product API, air-gap bundle, degraded queue, playbooks
- CLI readiness: `keprix.integrations.petraclus_provision`
- Tests: 18 passed under `domain-packs/petraclus/tests`

## Archived prompts

00 architecture through 05 contract tests / pilot / sign-off.
