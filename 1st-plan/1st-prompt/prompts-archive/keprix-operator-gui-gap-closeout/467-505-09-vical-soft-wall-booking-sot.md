# Prompt 476 / 09: viCal Soft Wall booking source-of-truth handoff (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `soft_wall_handoff_on_vical_confirmed` wired from viCal booking confirm side effects
- Soft Wall lead stage `booked` + linked Soft Wall booking notes; CRM stage when present
- Soft Wall bookings page prefers viCal SoT with mesh links
- Tests + docs shared with enroll prompt (`soft-wall-enroll-vical`)


**Depends on:** 467, existing viCal + Soft Wall bookings
**Blocks:** 481, 503
**Aligns with:** CRM 445

## Goal

Unify booking so Soft Wall does not rely on a bare `default_booking_link` when
viCal host profiles exist. CRM/outreach stages update on confirmed booking.

## Must-haves

1. Soft Wall campaign/sequence step can bind `vical_event_type_id` / public
   `/book/{slug}` with UTM/crm/outreach ids.
2. On viCal booking confirmed: update Soft Wall lead stage + activity; set
   metadata `vical_booking_id`; CRM stage `booked` when CRM present.
3. UI: Soft Wall bookings page and viCal hub show mesh "Open CRM/Outreach/Calendar".
4. Prefer viCal as SoT; avoid duplicate Soft Wall-only booking rows when viCal
   booking exists (migrate or link).
5. Missing viCal host fails honestly in GUI.
6. Agent tool `offer_booking` returns deep links.
7. Tests: confirm booking updates Soft Wall (+ CRM if mounted).
8. Docs: booking handoff runbook.

## Acceptance

- [x] Confirmed book appears on Soft Wall timeline and viCal
- [x] Mesh links both ways
- [x] No silent dual SoT conflict in happy path

## Done When

Funnel booking is Keprix-native end-to-end.
