# Prompt XCS-05: Xeclone evaluations, migration, cutover, and sign-off

**Status: COMPLETED 2026-08-08**
**Depends on:** XCS-00 through XCS-04

## Goal

Prove persona quality, privacy, consent and operational parity at every migration
wave before reducing Carina responsibilities.

## Must-haves

1. Golden evaluations for voice/style, factual grounding, relationship privacy,
   refusal, disclosure, consent, public/private separation and multimodal identity.
2. Human owner blind review compares Carina and Keprix drafts for fidelity,
   usefulness, hallucination, safety and unacceptable persona drift.
3. Adversarial tests: impersonate another person, remove disclosure, retrieve
   private chats, social-engineer a voice payment request, bypass approval, replay
   webhook, forged consent, malicious archive and cross-tenant query.
4. Media tests verify source consent, identity similarity within approved purpose,
   watermark/metadata, provider transfer and deletion propagation.
5. Wave gates: shadow draft, Keprix draft with Carina approval, inbound migration,
   vault/token migration, media jobs, then separately approved autonomous mode.
6. Each gate includes traffic percentage, observation period, metrics, stop limits,
   fallback owner and one-command or documented rollback.
7. Reconcile drafts, approvals, schedules, publishes, inbound events, memory and
   Scout audit before and after cutover; no duplicate actions or orphan artifacts.
8. Archive only after owner consent/sign-off and actual production profile is
   documented honestly.

## Acceptance

- [ ] Owner quality and privacy thresholds pass
- [ ] Every migration wave rolls back without lost or duplicate channel action
- [ ] Consent revocation propagates through all modalities
- [ ] Autonomous mode remains off unless separately signed

## What was built

- Eval suite + adversarial checks; sign-off READY local/staging; autonomous OFF

