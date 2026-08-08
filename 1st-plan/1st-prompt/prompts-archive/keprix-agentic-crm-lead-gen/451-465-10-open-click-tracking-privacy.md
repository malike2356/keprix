# Prompt 460 / N10: Open and click tracking (privacy toggle)

**Status: COMPLETED 2026-08-08** (P5 Nice)  
**Series:** 429-465  
**Depends on:** 443, 447, 448  
**Blocks:** none  
**Writing style:** plain ASCII only.

## What was built

- Open/click tracking privacy toggle

## Goal

Optional open/click tracking with privacy toggle. Hardening review marks this secondary; ship only as opt-in Nice.

## Must-haves

1. Workspace setting default **off**; per-campaign override.
2. Link wrapper and optional pixel with honest disclosure in email footer when on.
3. Bot/privacy noise: dedupe opens; do not treat open as strong buying signal in stage machine.
4. Metrics separate from reply/book (447).
5. Suppression of tracking for contacts with tracking opt-out.
6. Docs: privacy implications.
7. Tests: flag off means raw links; flag on wraps once.

## Acceptance

- [x] Default campaigns have no pixel
- [x] Opt-in campaign records click events
- [x] Stage automation does not auto-jump on open alone

## Done When

Tracking is available without becoming a vanity metric trap.
