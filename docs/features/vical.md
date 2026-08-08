# viCal (Keprix)

Keprix booking product ported from Propreneur **viCal** (Verlox Integrated Calendar). Behavioural reference lives in `propreneur/propreneur-v2` (`app/Services/Vcal/`, `vcal_*` tables). This is not Cal.com.

## Status

Shipped (prompts 377-388, with 387 deposit scaffold):

- Domain store + Consultation seed + host public slug
- Slot engine + locks + workspace busy
- Booking lifecycle + calendar bridge + conferencing URL template
- HTTP `/api/vical/*` (host + public)
- ECHO delegates when `KEPRIX_VICAL_ENABLED` is on (default)
- Host hub `/vical` and guest `/book/{slug}` (+ cancel/reschedule/embed)
- ICS download, reminder runner, optional webhooks
- Intake pools + disqualify
- Deposit scaffold via `price_data` (no new Stripe catalog prices)

## Persistence

JSON under `{KEPRIX_DATA_DIR}/workspace/vical_store.json`, same pattern as `calendar_store.json`.

Confirmed bookings bridge into the workspace calendar so `/calendar` and CalDAV push stay the shared time surface.

Deep links:

| From | To |
| --- | --- |
| `/vical?booking={id}` | Selects that booking on the host hub (Bookings tab) |
| `/calendar?event={id}` | Opens the bridged workspace event |
| Calendar event with `metadata.vical_booking_id` | **Open booking** → `/vical?booking=...` |
| Week/day empty hour on `/calendar` | Host create booking dialog (`POST /api/vical/bookings`, `skip_slot_check`) |

## Public guest routes

| Method | Path |
| --- | --- |
| GET | `/api/vical/public/hosts/{slug}` |
| GET | `/api/vical/public/hosts/{slug}/slots` |
| GET/POST | `/api/vical/public/hosts/{slug}/intake` (+ `/validate`) |
| POST | `/api/vical/public/hosts/{slug}/bookings` |
| POST | `/api/vical/public/cancel` |
| POST | `/api/vical/public/reschedule` |
| GET | `/api/vical/public/bookings/by-token` (+ `/ics`) |

Frontend: `/book/{slug}`, `/book/{slug}/cancel`, `/book/{slug}/reschedule`, `/book/embed/{slug}`, host hub `/vical`.

## Feature flags

| Env | Purpose | Default |
| --- | --- | --- |
| `KEPRIX_VICAL_ENABLED` | ECHO/voice cutover | `1` |
| `KEPRIX_VICAL_REMINDERS` | Reminder scheduler | `1` |
| `KEPRIX_VICAL_REMINDER_24H_MIN` | Minutes before start for 24h window | `1440` |
| `KEPRIX_VICAL_REMINDER_1H_MIN` | Minutes before start for 1h window | `60` |
| `KEPRIX_VICAL_WEBHOOKS` | Outbound lifecycle webhooks | `1` |
| `KEPRIX_VICAL_SMS_ON_CONFIRM` | SMS on confirm (Twilio if configured) | `0` |
| `KEPRIX_VICAL_CALENDAR_SYNC` | Prefer workspace/CalDAV path docs | `1` |
| `KEPRIX_VICAL_DEPOSITS` | Deposit scaffold | `1` |
| `KEPRIX_VICAL_UNPAID_TTL_MIN` | Auto-cancel unpaid | `60` |

## Deposits (scaffold)

Paid event types use `requires_deposit`, `deposit_minor`, `deposit_currency`. Checkout records a **price_data** shaped amount (same pattern as Keprix coffee donations). Do not create Stripe Prices from Hub. Complete locally with `/api/vical/deposits/mock-pay` or host `mark-paid`.

Stripe SoT for any later live pins: `/opt/lampp/htdocs/verlox/.access/.stripe-credentials-and-price-id.md` (never paste secrets into docs or chat).

## Calendar sync runbook

1. Confirm booking (calendar bridge writes workspace event).
2. CalDAV push sources on `/calendar` mirror workspace events (primary).
3. Optional host `meeting_url_template` for Meet/Zoom style links.
4. Do not invent a second OAuth stack unless CalDAV/GWS already cannot cover the host.

## Ops smoke

```bash
cd keprix
PYTHONPATH=src pytest tests/vical tests/personas/test_echo_scheduler.py -q
```

Manual:

1. Open `/vical`, seed defaults, copy public link.
2. Book as guest on `/book/{slug}`.
3. Confirm event on `/calendar`.
4. Cancel via guest token page.
5. With `KEPRIX_VICAL_ENABLED=0`, ECHO falls back to legacy invent for soak if needed.

## Packages

| Path | Role |
| --- | --- |
| `src/keprix/vical/*.py` | Domain, slots, lifecycle, ICS, reminders, intake, deposits, routes |
| `frontend/.../vical/page.tsx` | Host hub |
| `frontend/.../book/**` | Public funnel + embed |
| `docs/features/vical.md` | This runbook |

## Prompts

Programme folder: `keprix/1st-plan/1st-prompt/pending-prompts/keprix-vical-booking/`
