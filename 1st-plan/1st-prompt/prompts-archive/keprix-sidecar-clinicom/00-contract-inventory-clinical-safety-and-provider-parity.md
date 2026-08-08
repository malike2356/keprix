# Prompt CLS-00: Clinicom contract inventory, clinical safety, and provider parity

**Status: COMPLETED 2026-08-08**
**Depends on:** Clinicom AGENTS, sidecar governance, contract 2.0, shared contract
**Blocks:** CLS-01 through CLS-05

## Goal

Audit the existing Keprix Clinicom pack, Carina live pack, local clone and product
API, then lock safe parity and cutover criteria without changing the live profile.

## Must-haves

1. Inventory `keprix/domain-packs/clinicom`, Carina Clinicom pack, local sidecar,
   `/api/interpret`, `/api/capabilities`, provider settings, sessions, HCI,
   Easy Read, meds, explain, EHR, audit, consent, entitlements and deep AI tools.
2. Produce machine-readable contract matrix for every v2 tool: schema, status,
   source, model/dependency, latency, locale, modality, entitlement, safety class,
   deterministic fallback and current provider parity.
3. Preserve northbound compatibility: `/health`, `/clinicom/capabilities` and
   `/clinicom/tools/{name}`. Add shared `/v1/products/clinicom/*` only as an
   additive contract, never a cutover-breaking replacement.
4. Define responsibility: Clinicom owns patient/session truth, consent, auth,
   entitlements, EHR, UI and clinical workflow; Keprix performs scoped communication
   transformations and assists safety/handoff, not diagnosis or clinical decisions.
5. Create clinical safety hazard log for mistranslation, omitted negation, dosage/
   number distortion, wrong speaker/language, delayed audio, unsafe simplification,
   overconfident triage, hallucinated medication and failed human escalation.
6. Define safety invariants: preserve meaning/numbers/negation, confidence and
   provenance, never diagnose/prescribe, visible AI/fallback state, clinician
   acceptance where required, urgent-risk handoff and original-text availability.
7. Threat-model patient data leakage, cross-organisation session access, prompt
   injection in utterances, EHR overreach, malicious audio/files, token replay,
   model retention and OPS boundary violations.
8. Update docs that incorrectly call Keprix production default. Contabo truth is
   Carina until profile and smoke prove otherwise.

## Acceptance

- [ ] Every current tool and schema has a parity/safety disposition
- [ ] Hazard log has owner, controls, detection and residual risk
- [ ] No diagnostic or autonomous treatment capability is introduced
- [ ] Live Contabo routing remains unchanged

## What was built

- Contract matrix, hazard log, threat model, responsibility boundary, inventory docs
- Contabo docs corrected: Carina live, Keprix prepared only
