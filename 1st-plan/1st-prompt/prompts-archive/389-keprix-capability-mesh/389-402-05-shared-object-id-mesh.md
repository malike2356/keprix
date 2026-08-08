# Prompt 394 / 05: Shared object ID mesh

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 390 / 01  
Blocks: 396, 398  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Neural links fail without durable foreign keys. viCal already has `workspace_event_id`; contacts and research need the same discipline.

## Goal

Define canonical object types + ID link conventions and implement missing links for the pilot vertical.

## Must-haves

1. Catalog of object types: `contact`, `calendar_event`, `vical_booking`, `company_number`, `document`, `session`, `memory_item` (extend carefully).
2. Conventions: which field names carry links (`contact_id`, `workspace_event_id`, `vical_booking_id` in event metadata, …).
3. Pilot wiring:
   - booking create accepts/stores `contact_id`
   - confirmed booking metadata on calendar event includes `vical_booking_id`
   - helper to resolve graph hop: booking -> event -> contact
4. Tests for persistence and resolve helpers.
5. Graph edges updated (`via_id_field`).

## Nice-to-haves

1. Best-effort auto-match guest email to contact on public book.

## Acceptance

- [ ] Create booking with contact_id round-trips.
- [ ] Calendar event can be resolved back to booking id.
- [ ] Docs describe ID contract.
