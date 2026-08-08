# Prompt CLS-02: Clinicom product API, context, events, and minimisation

**Status: COMPLETED 2026-08-08**
**Depends on:** CLS-00, CLS-01
**Blocks:** CLS-03 through CLS-05

## Goal

Give the Keprix pack only the minimum organisation/session context needed while
keeping patient, EHR, acceptance and audit truth in Clinicom.

## Must-haves

1. Common health, capabilities, token exchange, context and event ack endpoints
   under `/api/keprix/v1`, additive to current Clinicom APIs.
2. Context slices: runtime provider policy, organisation language/specialty and
   communication preferences, current consent, session-safe glossary, turn by id,
   clinician-approved template and entitlement. Default excludes patient identity.
3. Keprix receives opaque organisation/session/turn ids. Identifiers, NHS number,
   address, EHR payload and full history require an explicit narrower product-side
   need and are not required for normal translate/simplify/speak.
4. Product action endpoints accept transformation result, explanation, digest or
   safety-assist suggestion as a proposal. Clinicom validates session version,
   consent, clinician role and acceptance before durable write or EHR handoff.
5. Events: session/turn started, consent changed, transform requested/completed/
   accepted/edited/rejected, handoff, safety acknowledged, provider changed,
   retention/deletion and entitlement changed. Sign, dedupe and minimise payloads.
6. EHR routes are not sidecar tools. Keprix may draft a bounded communication
   artifact; Clinicom controls FHIR mapping, clinician confirmation and EHR write.
7. Deletion/retention event purges Keprix jobs, transient media, cached context,
   RAG references and generated artifacts with completion acknowledgement.
8. Cross-organisation, impersonation, readonly roles, expired consent and stale
   session version fail closed in product and connector tests.

## Acceptance

- [ ] Common interpreter calls need no direct patient identifier
- [ ] Keprix cannot write EHR or accept its own output
- [ ] Consent revocation blocks/cancels relevant work
- [ ] Product and Keprix audit correlate without duplicating clinical records

## What was built

- Clinicom /api/keprix/v1 connector (health, capabilities, token exchange, context, events, proposals)
- Proposal-only transforms; no EHR write from Keprix
