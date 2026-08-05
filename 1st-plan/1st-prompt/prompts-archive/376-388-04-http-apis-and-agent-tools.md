# Prompt 380 / 04: HTTP APIs and agent tools

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 379 / 03  
Blocks: 381, 382, 383  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Propreneur exposes hub REST, public book controllers, and Carina tools (`ScheduleSessionTool`, availability tools). Keprix needs equivalent HTTP + tools without bypassing locks.

## Goal

Ship authenticated host APIs, public booking APIs (token/slug scoped), and agent tools so GUI and chat share one engine.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Propreneur tenant API | `routes/tenant_vcal_api.php`, `Api/Vcal/*` |
| Public controllers | `PublicBookingController.php` |
| Carina tools | `CheckVcalAvailabilityTool.php`, `ListVcalEventTypesTool.php`, `ScheduleSessionTool.php` |
| Keprix API mount | `src/keprix/api/server.py` |
| GWS pattern | `tools/google_workspace_tools.py` (confirm gates) |
| ECHO API | `/api/personas/echo/book`, `/slots` |

## Must-haves

1. Mount router prefix e.g. `/api/vical/` (or `/api/companies-house`-style consistency under `/api/vical`):
   - Host auth: event-types CRUD, availability CRUD, blackouts CRUD, bookings list/get, approve/reject/cancel/reschedule, notes.
   - Public (limited): resolve slug, list active event types, offer slots, create booking, cancel/reschedule by guest token.
   - Status: `/api/vical/status` (`enabled`, configured defaults).
2. Agent tools (names kebab or Keprix colon style; pick one matching `_KEPRIX_CORE_TOOLS`):
   - `vical-list-event-types`
   - `vical-offer-slots`
   - `vical-create-booking` (requires confirm / Rule-of-Two gate if destructive policy applies)
   - `vical-cancel-booking` / `vical-reschedule-booking`
3. ACL: register tools in toolsets; deny-by-default where 373 pattern exists.
4. Do not break existing `/api/workspace/calendar` routes.
5. OpenAPI or feature doc endpoints listed in `docs/features/vical.md` and agent-surface access doc if present.
6. Tests: API happy path + unauthorized + double-book conflict.

## Nice-to-haves

1. Public REST API-key mode like Propreneur `vcal.api_key`.
2. Alias tools that ECHO prompts can call by older names if any existed in archives (`calendar.book_appointment` text only: implement as wrapper, not second engine).

## Ultimate

1. Mobile-friendly booking list endpoints mirroring Propreneur mobile vcal.

## Acceptance

- [ ] Authenticated host can CRUD event type and see bookings JSON.
- [ ] Public create uses locks; conflict returns 409-class error.
- [ ] Agent tool offer-slots returns real engine output.
- [ ] `docs/features/vical.md` lists routes + tools.
