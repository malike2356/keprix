# Prompt 397 / 08: Telegram slash UX + outbound reminders

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 396 / 07  
Blocks: 402  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Natural language is not enough for power users; reminders must return to the channel where the operator lives.

## Goal

Add Telegram-facing slash (or equivalent) for top pilot actions, and wire viCal reminder/notification path to `send_message` when a Telegram home target exists.

## Baseline

| Piece | Path |
|---|---|
| Slash | `gateway/slash_commands.py`, `gateway/slash/telegram.py` |
| send_message | `tools/send_message_tool.py` |
| viCal reminders | `vical/reminders.py`, `reminder_scheduler.py` |
| Cron deliver | `cron/scheduler.py` |

## Must-haves

1. Slash commands for: next slots, book (guided), my bookings, cancel-by-id-or-token (safe).
2. On reminder send, attempt Telegram outbound via existing deliver/`send_message` patterns when configured; else keep notification outbox behaviour.
3. Feature flag or env for channel outbound (`KEPRIX_VICAL_CHANNEL_REMINDERS` default conservative if needed).
4. Tests for slash registration and reminder outbound with mocked transport.

## Acceptance

- [ ] Slash list includes pilot commands on telegram platform.
- [ ] Reminder path documents how to enable Telegram delivery.
- [ ] Failure to send does not corrupt booking state.
