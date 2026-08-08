# Ref 376: Keprix viCal booking adoption (build order)

Status: FILED COMPLETED 2026-08-04  
Series living queue: `../pending-prompts/keprix-vical-booking/`  
Source behaviour: `/opt/lampp/htdocs/verlox/propreneur/propreneur-v2` viCal (`Vcal`, `/vical`, `booking_calendar`)  
Integration targets: Keprix workspace calendar + ECHO + GWS/CalDAV

## Order

| ID | File | Intent |
|---|---|---|
| 376 | 00 overview | Guardrails, naming, integration contract |
| 377 | 01 domain/store | `vcal_*` persistence |
| 378 | 02 slots/locks/busy | Single free/busy with workspace calendar |
| 379 | 03 lifecycle + bridge bridge | Booking CRUD + calendar events |
| 380 | 04 HTTP + tools | APIs and `vical-*` agent tools |
| 381 | 05 public book | Guest funnel + embed |
| 382 | 06 host hub | `/vical` operator UI |
| 383 | 07 ECHO/voice unify | Existing booking clients switch to viCal |
| 384 | 08 reminders/ICS/webhooks | Notifications |
| 385 | 09 sync/conferencing | CalDAV/GWS first |
| 386 | 10 intake | Qualification pools |
| 387 | 11 deposits | Owner-gated Stripe; existing price IDs only |
| 388 | 12 tests/cutover/archive | Ship gate |

## Parallelism

- 05 and 06 can parallel after 04.
- 08 can parallel with 05/06 after 03.
- 07 should wait for 03+04.
- 11 waits for explicit owner approval.
- 12 last.

## Non-goals

Cal.com; Propreneur PHP runtime inside Keprix; new Stripe prices without owner ask; mentorship/property accounting ports.
