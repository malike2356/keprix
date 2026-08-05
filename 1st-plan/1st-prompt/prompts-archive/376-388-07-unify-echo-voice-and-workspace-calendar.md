# Prompt 383 / 07: Unify ECHO, voice, and workspace calendar with viCal

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 379 / 03, 380 / 04  
Blocks: 388  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

This is the critical "integrate with existing booking system" prompt. ECHO and voice already book. They must become **clients** of viCal, not parallel engines.

## Goal

Wire `EchoScheduler`, `/api/personas/echo/*`, and voice receptionist booking paths through viCal slots + lifecycle, while preserving workspace calendar visibility and confirmation UX.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| ECHO scheduler | `src/keprix/personas/echo/scheduler.py` |
| ECHO receptionist | `src/keprix/personas/echo/receptionist.py` |
| Booking prompt | `src/keprix/personas/echo/prompts/booking.md` |
| ECHO API | `src/keprix/personas/routes.py` |
| Skill | `src/keprix/skills/productivity/calendar-booking/SKILL.md` |
| Voice receptionist | `src/keprix/voice/personas/receptionist.py`, settings page |
| Tests | `tests/personas/test_echo_scheduler.py`, `test_echo_receptionist.py` |

## Must-haves

1. `EchoScheduler.find_available_slots` delegates to SlotEngine for default event type (seeded Consultation), falling back to legacy fixed hours only if `KEPRIX_VICAL_ENABLED=0`.
2. `book_appointment` creates a viCal booking with `source=echo` (or `voice`) and still returns `BookingResult` shape for receptionist compatibility (`event_id` = workspace event id).
3. `/api/personas/echo/slots` and `/book` keep URLs; internals call viCal.
4. Voice confirmation gate still applies before create; after confirm, same lifecycle.
5. Prompt/skill text: teach agent to use `vical-*` tools; forbid inventing availability.
6. Feature flag dual-path for safe cutover; document default-on once tests green.
7. Regression tests updated; no second busy invent.

## Nice-to-haves

1. Map ECHO session metadata (caller phone) into booking notes.
2. Persona can select among multiple event types if host configured more than one.

## Ultimate

1. Retire legacy 09-17 invent code path entirely after soak.

## Acceptance

- [ ] ECHO book creates `vcal_bookings` row + calendar event.
- [ ] Slot offered by ECHO never overlaps existing calendar event.
- [ ] Flag off restores previous behaviour for break-glass.
- [ ] Persona tests pass with viCal backend mocked or sqlite/json store.
