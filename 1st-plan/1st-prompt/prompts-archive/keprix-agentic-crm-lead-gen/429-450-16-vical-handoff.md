# Prompt 445 / 16: viCal handoff on qualified or booked

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 444  
**Blocks:** 447  
**Writing style:** plain ASCII only.

## What was built

- Implemented in crm/ Soft Wall glue + UI + tests (442-448 wave)

## Goal

When a lead is qualified, outreach uses real viCal booking (not only a template link), and CRM stores booking ids.

## Must-haves

1. Replace Soft Wall `default_booking_link` only paths with optional `vical_event_type_id` / public book URL from host profile.
2. On stage `qualified`, Soft Wall or auto message includes `/book/{slug}` deep link with UTM/crm ids if supported.
3. On viCal booking confirmed, webhook/listener sets CRM stage `booked`, Activity, Deal touch; metadata `vical_booking_id`.
4. Calendar already bridges viCal -> workspace event; CRM detail shows Open
   booking / Open calendar (mesh links). Deal/booked stage surfaces same CTAs.
5. Agent tool `crm_offer_booking(contact_id)` returns GUI deep links.
6. Tests: confirm booking updates CRM; missing viCal host fails honestly.
7. Soft Wall stage suggestion to `booked`/`qualified` visible in `/crm/inbox`.

## Acceptance

- [x] Confirmed guest book appears on CRM timeline
- [x] No duplicate Soft Wall outreach_bookings required (prefer viCal as SoT)
- [x] Mesh links work both ways from CRM, calendar, and viCal
- [x] Offer booking actionable from lead/contact detail GUI

## Done When

Funnel end is Keprix-native booking.
