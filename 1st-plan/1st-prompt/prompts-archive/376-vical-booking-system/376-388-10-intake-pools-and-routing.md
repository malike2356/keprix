# Prompt 386 / 10: Intake pools and routing

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 381 / 05, 382 / 06  
Blocks: 388  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Propreneur intake pools qualify guests before slots. Useful for consultative Keprix hosts without dragging property-specific questions.

## Goal

Add intake pools (question sets + disqualify rules) attachable to event types, enforced on public book and optionally agent/ECHO creates.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Migration | `2026_05_12_150000_vical_intake_pools_and_routing.php` |
| Services | `VcalIntakeValidator.php`, `VcalIntakeRoutingApplicator.php` |
| Alpine UI | `resources/js/alpine/vical-intake-questions.js` |
| Help | `resources/docs/help/vcal-bookings/` intake sections |

## Must-haves

1. `vcal_intake_pools` store + CRUD in hub.
2. Questions support text, single-select, multi-select; optional disqualify answers.
3. Public book: show intake before slots when pool attached; disqualify shows friendly stop page; store answers on booking.
4. Agent create may pass `intake_answers` or skip when `source` is echo/voice (document policy: prefer skip for voice, require for public).
5. Tests for disqualify and pass-through.

## Nice-to-haves

1. Route different event types based on answers (light applicator).
2. Export disqualified leads to Contacts as tagged leads.

## Ultimate

1. Full Propreneur routing to mentorship programmes (out of scope for Keprix).

## Acceptance

- [ ] Guest failing intake cannot see slots.
- [ ] Passing guest can book; answers visible on booking detail.
- [ ] Hub can attach pool to event type.
