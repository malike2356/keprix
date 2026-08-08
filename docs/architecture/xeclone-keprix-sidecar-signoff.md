# Xeclone Keprix sidecar sign-off

**Date:** 2026-08-08
**Product:** xeclone / iLaud
**Pack version:** 0.1.0
**Contract version:** 1.0.0
**Persona:** ilaud@0.1.0
**Port:** 3361

## Verdict

**READY for local/staging pilot only.**

## Conditions

1. Autonomous mode is **OFF** unless separately signed.
2. Carina remains the Phase 1 live path for inbound webhooks and OAuth.
3. Media providers are deterministic stubs; no production ElevenLabs/HeyGen from this pack.
4. Shadow dual-run must never publish.
5. Provision receipts must never include secrets.
6. Contabo / carinaai.uk were not modified by this pack work.
7. Production cutover requires a later owner gate with traffic, metrics and rollback.

## Evidence expected

- `pytest domain-packs/xeclone/tests -q` green
- Health and capabilities expose all XCS-01 nodes
- Consent revoke and other-person media rejection covered
- Approve-once / publish-once / kill switch covered
- Adversarial eval script present under `domain-packs/xeclone/evals/`
