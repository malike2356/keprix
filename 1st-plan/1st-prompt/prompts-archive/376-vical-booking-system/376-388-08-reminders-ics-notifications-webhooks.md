# Prompt 384 / 08: Reminders, ICS, notifications, webhooks

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 379 / 03  
Blocks: 388  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Propreneur sends guest confirm / cancel / reschedule / reminder mails and ICS. Keprix ECHO only queues confirmation dicts. Guests need durable reminders.

## Goal

Ship ICS generation, guest/host notification hooks, 24h and ~1h reminders, and optional outbound lifecycle webhooks.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Reminder service | `propreneur-v2/app/Services/Vcal/VcalBookingReminderService.php` |
| ICS | `VcalIcsFormatter.php` |
| Mails | `app/Mail/Vcal/*` |
| Command | `VcalSendBookingRemindersCommand.php` |
| Config | `config/vcal.php` reminder windows |
| Keprix notifications | existing notification / email paths if any; else document SMTP/env requirements |
| Webhooks Propreneur | `DispatchVcalBookingIntegrationWebhooks.php` |

## Must-haves

1. ICS attachment/download for confirmed bookings (UID stable across reschedule where possible).
2. Notification templates (email at minimum) for: received, confirmed, cancelled, rescheduled, reminder.
3. Reminder runner: mark columns `reminder_24h_sent_at` / `reminder_1h_sent_at` (or equivalent); idempotent; env windows like Propreneur.
4. Wire runner into Keprix scheduler / cron catalog (do not leave orphan command).
5. Optional webhooks: POST JSON `{event, payload, sent_at}` with HMAC signature header; events `vical.booking.*`.
6. SMS on confirm only if Twilio already configured; default off (`KEPRIX_VICAL_SMS_ON_CONFIRM=0`).
7. Tests for reminder idempotency + ICS parseability.

## Nice-to-haves

1. In-app notification row for host on pending_review.
2. Prefer workspace notification settings module if present.

## Ultimate

1. Comms Hub style sequence enroll (skip; Propreneur-specific).

## Acceptance

- [ ] Confirmed guest can download valid ICS.
- [ ] Reminder command sends once per window.
- [ ] Webhook signature verified in unit test with fixture secret (not real secrets).
- [ ] Docs cover how to enable reminders in Docker/CE.
