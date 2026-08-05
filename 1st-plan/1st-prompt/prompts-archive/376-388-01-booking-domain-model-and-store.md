# Prompt 377 / 01: Booking domain model and store

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 376 / 00  
Blocks: 378+  
Do not ask clarifying questions unless blocked by missing credentials or destructive ops.  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Without first-class `vcal_*` records, Keprix cannot express event types, blackouts, guest tokens, or booking statuses. ECHO today only writes ad-hoc calendar events.

## Goal

Land durable, user/workspace-scoped booking domain types and persistence that mirror Propreneur `vcal_*` enough for Keprix to become the booking system of record alongside (not instead of) workspace calendar events.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Propreneur tables | `propreneur-v2/database/migrations/tenant/2026_05_02_630000_create_vical_tables.php` + later `*vcal*` migrations |
| Models | `propreneur-v2/app/Models/Tenant/Vcal/*` |
| Keprix calendar store | `src/keprix/workspace/repository.py`, `docs/features/calendar.md` |
| Archived calendar schema intent | `prompts-archive/10-workspace-documents-notes-calendar.md` |

## Must-haves

1. Domain types / tables (names may use `vcal_` prefix):

| Entity | Minimum fields |
|---|---|
| `vcal_event_types` | id, user/workspace scope, host_user_id, slug, name, duration_minutes, buffer_before/after, min_notice_minutes, horizon_days, location_mode, requires_approval, requires_deposit, deposit_minor/currency nullable, intake_pool_id nullable, active, metadata JSON, timestamps |
| `vcal_availability_rules` | id, scope, host_user_id or event_type_id, day_of_week, start_time, end_time, timezone |
| `vcal_blackout_dates` | id, scope, host_user_id nullable, start/end (date or timestamptz), reason |
| `vcal_bookings` | id, scope, event_type_id, host_user_id, guest_name, guest_email, starts_at, ends_at, status, guest_token, meeting_url, workspace_event_id nullable, source (`public`/`api`/`agent`/`echo`/`voice`), intake_answers JSON, notes, session_outcome nullable, cancel/reschedule metadata, timestamps |
| `vcal_slot_locks` | id, scope, host_user_id, starts_at, ends_at, holder_token, expires_at |

2. Status enum aligned with Propreneur lifecycle: `pending_payment`, `pending_review`, `confirmed`, `cancelled`, `rejected`.
3. Indexes: scope + host + time range on bookings; unique `guest_token`; lock expiry prune key.
4. Repository API with isolation checks (never read/write another user's bookings by raw id alone).
5. Seed helper: one default event type (e.g. "Consultation", 30 min) + weekday windows matching prior ECHO 09-17 defaults so cutover is non-surprising.
6. Document persistence choice (Postgres vs JSON under data root) and migration path in feature stub `docs/features/vical.md`.
7. Do **not** delete or stop writing workspace calendar events; bridge lands in 03.

## Nice-to-haves

1. `vcal_api_keys` for public REST later.
2. Soft link field `contact_id` for Contacts when present.

## Ultimate

1. Dual-write audit log for booking status transitions.

## Out of scope

Slot maths, HTTP UI, Stripe, ECHO rewrite (those are 02+).

## Delivery order

1. Types + store + tests.
2. Seed helper.
3. Short docs stub.

## Acceptance

- [ ] Can insert event type + rule + blackout + booking in pytest.
- [ ] Range query by host + time is covered by a test.
- [ ] Default seed creates Consultation-like type usable by 07.
- [ ] Docs point to propreneur-v2 as behavioural source, not copy-paste PHP.
