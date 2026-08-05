---
name: mesh-book-and-notify
description: Offer viCal slots, book a guest, optionally notify via send_message. Promote to cron for follow-ups.
---

# Mesh: book and notify

## When to use

Operator wants to schedule a Consultation (or other viCal type) from chat/Telegram and optionally ping a channel.

## Steps

1. Call `vical_offer_slots` with desired count.
2. Pick a slot `start_at`.
3. Call `vical_create_booking` with guest_name, guest_email, starts_at, optional contact_id.
4. Confirm calendar bridge via `calendar_list_events` around that time.
5. Optional: `send_message` to operator home/Telegram with booking id.

## Cron promote

Use Agent OS skill-to-cron templates to schedule a reminder job that lists upcoming bookings and sends a digest when `KEPRIX_VICAL_CHANNEL_REMINDERS=1`.
