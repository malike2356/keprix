# Prompt 385 / 09: External calendar sync and conferencing

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 379 / 03, prefer 384  
Blocks: 388  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Propreneur syncs bookings to Google/Outlook and creates Zoom/Meet/Teams links. Keprix already has CalDAV push and GWS create tools. Unify rather than invent a third OAuth stack when possible.

## Goal

On confirm, ensure meeting links and external calendar mirrors use existing Keprix connectors first; add narrowly scoped OAuth only if CalDAV/GWS cannot cover host needs.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Propreneur sync | `VcalCalendarSyncService.php`, jobs `SyncVcalBookingToCalendarJob` |
| Conferencing | `Conferencing/VcalConferencingService.php` + adapters |
| Keprix CalDAV | `calendar_sync.py`, sources UI on `/calendar` |
| GWS | `tools_calendar.py`, OAuth bridge |
| Docs | `docs/features/calendar.md` |

## Must-haves

1. On confirm: if host has CalDAV push source, rely on workspace event push (already from 03). Document as primary path.
2. Optional: when GWS connected, also upsert Google event with `vical_booking_id` extended property; avoid duplicate when CalDAV already targets Google.
3. Conferencing: at least one of:
   - manual meeting_url field, or
   - Google Meet via GWS when available, or
   - Zoom when Keprix already has Zoom integration config
4. Busy reader from 02 should consume the same connectors.
5. Feature flag `KEPRIX_VICAL_CALENDAR_SYNC` default conservative if new OAuth required.
6. Never paste OAuth client secrets into repo; use `.access` / env pattern already used for GWS.
7. Tests with mocked HTTP for connector upsert/delete on cancel.

## Nice-to-haves

1. Microsoft Graph path when MS connector lands.
2. Full Propreneur-style `vcal_calendar_connections` table if CalDAV is insufficient.

## Ultimate

1. Bidirectional sync of external cancels back into viCal (careful conflict rules).

## Acceptance

- [ ] Confirm booking appears on `/calendar` and, when CalDAV push configured, attempts external sync without erroring the booking.
- [ ] Cancel clears or updates external event when id known.
- [ ] Meeting URL persisted when adapter returns one.
- [ ] Runbook lists which connector to use first.
