# Prompt 396 / 07: Telegram pilot tools (viCal + calendar + contacts)

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 393 / 04, 394 / 05, viCal programme completed  
Blocks: 397, 398  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Prove the spider web on one vertical end-to-end in Telegram: schedule, see calendar, attach people.

## Goal

Ship first-class agent tools for viCal + calendar + contacts, add to `_KEPRIX_CORE_TOOLS` so `keprix-telegram` inherits them, with ACL `check_fn` and domain service reuse (no second implementation).

## Must-haves

1. Tools (names can vary; keep clear):
   - list/offer viCal slots
   - create/cancel/reschedule booking (respect lifecycle)
   - list upcoming bookings
   - list calendar events in a range
   - find/create/get contact (minimal set)
2. Register + core toolset membership.
3. Capability graph nodes for `vical`, `calendar`, `contacts` marked `wired` for telegram when done.
4. Pytest for tool handlers (mocked store OK).
5. Update `agent-surface-access.md` + capability-mesh docs.

## Nice-to-haves

1. Voice/ECHO aliases already use viCal; document agent tool aliases.

## Acceptance

- [ ] With gateway + telegram toolset, agent can book a consultation via tool call in tests or staged smoke.
- [ ] Booking still appears on `/calendar` via existing bridge.
- [ ] No secrets in logs.
