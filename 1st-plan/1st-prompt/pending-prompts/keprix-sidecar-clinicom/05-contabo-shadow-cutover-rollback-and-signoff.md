# Prompt CLS-05: Clinicom Contabo shadow, cutover, rollback, and sign-off

**Status:** PENDING
**Depends on:** CLS-00 through CLS-04

## Goal

Prepare and prove Keprix on Contabo without violating the rule that Carina remains
live until the owner explicitly authorises the switch.

## Must-haves

1. Upload pinned Keprix Clinicom pack to `KEPRIX_CLINICOM_PACK_DIR`; verify
   `http_app.py`, checksum, image, contract and health. Starting the optional
   container does not change `CLINICOM_SIDECAR_PROFILE=carina`.
2. Shadow only redacted, consent-eligible staging or synthetic requests. Never
   double-play audio to users or let shadow output affect a clinical session.
3. Compare Carina/Keprix schema, availability, latency, fallback, preservation,
   confidence, safety and human review metrics over a defined observation window.
4. Run contract, isolation, forged-token, replay, deletion, load, outage, model
   rollback, bad-pack, restart and resource-pressure drills on the deployed path.
5. Produce clinical safety sign-off with unresolved hazard disposition, DPO/security
   review as applicable, operator readiness, incident contacts and stop thresholds.
6. Owner-approved cutover uses only
   `deploy/contabo-temp/switch-sidecar.sh keprix`. Immediately verify product
   `/api/health` reports `provider.profile=keprix`, product capabilities, sidecar
   health, interpreter fixtures, dashboard and audit.
7. Watch errors, latency, fallback, low-confidence and safety thresholds. Any hard
   threshold triggers `switch-sidecar.sh carina`, verification and incident note.
8. After every Contabo deploy, verify `https://carinaai.uk/` HTTP 200 and run the
   prescribed nginx repair if needed. Do not alter Clinicom OPS boundaries.
9. Document actual live state after the attempt. Failed or rolled-back cutover is
   not described as Keprix production.
10. Archive only after owner verdict READY and stable observation. Otherwise keep
    pending with evidence and Carina live.

## Acceptance

- [ ] Shadow output cannot enter clinical workflow
- [ ] Switch and rollback are each rehearsed and timed
- [ ] Live profile and contract are verified, not assumed
- [ ] Carina remains immediate known-good fallback

## Prep evidence (2026-08-08)

Built without live flip:

- `keprix/domain-packs/clinicom/docs/contabo-shadow-cutover.md`
- `clinicom-ai/deploy/contabo-temp/shadow-keprix.md`
- `clinicom-ai/scripts/shadow-keprix-compare.py`
- `keprix/domain-packs/clinicom/docs/clinical-safety-signoff.md` (Verdict: PENDING_OWNER)

Archive this prompt only after owner READY verdict and stable observation with Carina as fallback.
