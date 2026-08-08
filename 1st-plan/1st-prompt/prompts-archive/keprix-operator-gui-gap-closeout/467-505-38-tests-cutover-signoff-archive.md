# Prompt 505 / 38: Tests, cutover, sign-off, archive (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Sign-off doc; series archived; pending set cleared


**Depends on:** all prior in 467-504 + CRM sibling gate 481
**Blocks:** none

## Goal

Prove GUI gap closeout, cut over nav/flags, sign off, archive prompts.

## Must-haves

1. pytest + frontend smoke for every new Must route in this series.
2. Regression: Soft Wall core, contacts, `/data` existing tabs, mutation tools
   page still correct, Tool ACL nav fixed.
3. Sign-off doc `docs/architecture/operator-gui-gap-signoff.md` with Verdict
   READY/NOT READY and checklist covering Critical+High+Medium items.
4. CRM gate: if 481/466 not READY, overall Verdict cannot be READY for CRM
   Critical rows (may READY Soft Wall/data/fleet subsets with partial note).
5. Feature flags documented; edition gates verified.
6. Contabo: no marketing break; if any Contabo deploy occurs verify
   `carinaai.uk` and keprix marketing/app health per workspace rules.
7. Archive series to `prompts-archive/` when READY; update pending README;
   delete empty pending dirs; remove `_generate_series.py` if still present.
8. Do not archive partial without owner block note.

## Acceptance checklist (minimum)

- [x] Tool ACL GUI + nav fixed
- [x] Soft Wall deliverability, outbox, suppressions, contactability, merges,
      kill switches, enroll preflight, viCal SoT
- [x] Sheet preprocess API+GUI; discovery framework+GUI
- [x] CRM console READY or owner-blocked
- [x] Fleet + companion GUI
- [x] Data plane + jobs + ML + export GUI
- [x] Improvement, code-agent, typed agents, kernel, interfaces, intents,
      adapters, evals benchmarks, personas inventory
- [x] Nav orphans fixed; leads/opportunities clarity; hot-cache ops
- [x] Credential proxy ops GUI
- [x] Intentional API-only register committed
- [x] gui_catalog honest; docs shipped; tests green

## Done When

Series archived or explicitly owner-blocked with partial evidence.
