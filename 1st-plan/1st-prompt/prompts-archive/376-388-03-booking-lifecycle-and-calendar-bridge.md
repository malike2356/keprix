# Prompt 379 / 03: Booking lifecycle and calendar bridge

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 378 / 02  
Blocks: 380, 383  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Propreneur `VcalBookingService` is the lifecycle spine. Keprix must create durable bookings and keep workspace calendar as the shared time surface so `/calendar`, CalDAV push, and ECHO stay coherent.

## Goal

Implement create / approve / reject / cancel / reschedule / complete with status transitions, guest tokens, and mandatory bridge to `workspace_repo` calendar events.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Lifecycle | `propreneur-v2/app/Services/Vcal/VcalBookingService.php` |
| Notifier hooks | `VcalBookingNotifier.php` (wire thin stubs; full mail in 08) |
| Keprix create event | `workspace_repo.create_event` / calendar routes |
| ECHO book | `EchoScheduler.book_appointment` |

## Must-haves

1. `BookingLifecycle` methods covering Propreneur-equivalent transitions:
   - guest/agent create -> `pending_payment` | `pending_review` | `confirmed` per event type flags
   - host approve / reject
   - guest or host cancel (honour cancellation window if present)
   - reschedule (cancel+recreate or in-place; keep previous starts/ends in metadata)
   - mark outcome attended / no_show
2. On confirm (or create when auto-confirm): create workspace calendar event; store `workspace_event_id` on booking.
3. On cancel/reschedule: update or delete linked workspace event; avoid double Google push races by only writing through workspace event helpers (CalDAV push already attached there).
4. Guest token: cryptographically random, unique, used for public cancel/reschedule later.
5. Source field: `public` | `api` | `agent` | `echo` | `voice`.
6. Idempotency: replaying create with same lock/token does not double-book.
7. Tests for each transition + calendar bridge create/update/delete.

## Nice-to-haves

1. Emit internal events for webhooks in 08 (`vical.booking.confirmed`, etc.).
2. Notes + recording URL fields as on Propreneur hub.

## Ultimate

1. Soft contact upsert when guest email matches Contacts.

## Out of scope

HTTP routers (04), public UI (05), mail templates (08), Stripe (11).

## Acceptance

- [ ] Confirming a booking creates both `vcal_bookings` row and a `/calendar` event.
- [ ] Cancel removes or cancels the linked workspace event.
- [ ] Reschedule moves both booking times and linked event times.
- [ ] Approval-required types stay `pending_review` until approve.
