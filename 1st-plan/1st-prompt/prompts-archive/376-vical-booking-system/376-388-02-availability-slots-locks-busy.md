# Prompt 378 / 02: Availability, slots, locks, busy

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 377 / 01  
Blocks: 379+  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

ECHO invents slots from fixed business hours. viCal computes slots from rules, blackouts, buffers, existing bookings, and external busy. Without this, public book and ECHO will conflict.

## Goal

Implement a slot engine + short-lived locks that subtract Keprix workspace calendar busy (and optional CalDAV/GWS busy) so free/busy is single-sourced for booking flows.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Propreneur slots | `VcalSlotService.php`, `VcalSlotLockService.php` |
| Busy reader | `VcalExternalCalendarBusyReader.php` |
| Keprix busy today | `EchoScheduler.list_busy_events` -> `workspace_repo.list_events` |
| CalDAV sync | `src/keprix/workspace/calendar_sync.py` |
| GWS list | `tools_calendar.py` (`gws_calendar_list`) |

## Must-haves

1. `SlotEngine.offer_slots(event_type_id|slug, range, horizon)`:
   - Steps by duration (or 15-min grid then filter).
   - Applies weekly rules + timezone.
   - Subtracts blackouts, buffers around existing `vcal_bookings` in active statuses, and workspace calendar events for the host.
   - Honours min notice + horizon.
2. BusyReader union:
   - Always: workspace `calendar_store` events for host.
   - Optional: connected CalDAV busy / GWS freebusy when credentials exist (fail soft: log + continue without inventing success).
3. Slot locks: create/expire/release; booking create must hold a valid lock or re-check race.
4. Prune command or scheduler hook for expired locks (mirror `vcal:prune-slot-locks` intent).
5. Tests: overlap, buffer, blackout day, min notice, concurrent lock holds one winner.

## Nice-to-haves

1. Round-robin multi-host (Propreneur `VcalRoundRobinService`) only if event type has host pool metadata.
2. Daily booking caps per event type.

## Ultimate

1. Microsoft Graph busy when Keprix MS connector exists.

## Out of scope

Persisting bookings beyond lock + dry-run; full OAuth sync UI (09).

## Acceptance

- [ ] Given a busy workspace event, offered slots never overlap it.
- [ ] Two lock attempts for the same start: one wins.
- [ ] Engine returns empty list (not fake availability) when fully booked.
- [ ] ECHO-compatible default windows work via seeded rules from 01.
