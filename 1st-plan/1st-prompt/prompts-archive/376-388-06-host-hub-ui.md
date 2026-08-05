# Prompt 382 / 06: Host hub UI

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 380 / 04  
Blocks: 388  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Hosts need operator CRUD for event types, availability, blackouts, and booking management. Propreneur hub is `/vical`; Keprix needs the same job in MUI workspace chrome.

## Goal

Ship `/vical` host hub: event types, availability, blackouts, bookings list/detail (approve/reject/cancel/reschedule), link to calendar, copy public book URL.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Propreneur hub | `VicalController.php`, views under `resources/views/tenant/vical/` |
| Keprix calendar UI | `frontend/src/app/(workspace)/calendar/page.tsx` |
| Nav | `frontend/src/lib/navigation.ts`, `ui_contract/navigation.py` |
| Operator polish example | `frontend/.../companies-house/page.tsx` |

## Must-haves

1. Nav entry under Workspace (near Calendar): label `viCal` or `Bookings`, href `/vical`.
2. Hub sections (tabs or subroutes):
   - Overview / upcoming
   - Event types CRUD
   - Availability + blackouts
   - Bookings inbox (pending review + confirmed)
   - Booking detail actions
3. Copy public link (`/book/{slug}`) with slug management.
4. Dense, professional layout (split list/detail where useful); no text noticeboard.
5. Deep link from a booking to `/calendar` focused on that event when `workspace_event_id` exists.
6. Empty states with clear CTAs.
7. Frontend client module `lib/vical-api.ts`.

## Nice-to-haves

1. Simple week calendar inside hub (reuse calendar components).
2. Analytics tiles (Propreneur host analytics light).

## Ultimate

1. Group events / ticketing (defer unless owner expands scope).

## Acceptance

- [ ] Host can create event type + rules and see public URL.
- [ ] Approve pending booking from hub updates status via API.
- [ ] Nav appears for authenticated workspace.
- [ ] Mobile usable for booking inbox actions.
