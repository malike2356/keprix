# Customer Concierge v1 baseline audit (Prompt 629)

**Date:** 2026-08-09  
**Scope:** `keprix/`  
**Architecture:** `shared/workspace-governance/AIVA-KEPRIX-CUSTOMER-CONCIERGE-BOOKING.md`  
**Contract package:** `keprix/contracts/customer-concierge-v1/` (vendored from `shared/contracts/customer-concierge-v1/`)  
**Runtime dependency on Carina:** none

This table names exact modules to extend. Do not build parallel booking or CRM stores. Status values: **REUSABLE**, **INCOMPLETE**, **MISSING**, **OUT_OF_SCOPE**.

## Confirmed non-satisfying foundations

| Claim | Evidence path | Why it fails managed Concierge v1 |
| --- | --- | --- |
| Meeting URL templates = Zoom booking | `src/keprix/vical/conferencing/fallback.py` (`resolve_meeting_url`) | Historical gap code `zoom_meeting_create`; templates remain unmanaged fallback after 632 managed Zoom adapter |
| In-memory notification outbox = delivery | `src/keprix/vical/notifications.py` (`_OUTBOX`) | Process-local list; not durable; not proof of delivery |
| Operator support API = external customer support | `src/keprix/support/routes.py` (`require_api_auth`) | Authenticated operator surface; no audience principal or visitor ticket API |

Tests assert these gap codes: `zoom_meeting_create`, `durable_notification_delivery`, `external_customer_support_api`.

## Evidence table

### 1. Concierge setup / publish (Prompt 628)

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | `src/keprix/customer_concierge/{store,routes,readiness,widget,prompt_overlay}.py` | Setup wizard, publish gate, persona overlay |
| REUSABLE | `frontend/src/app/(workspace)/concierge/page.tsx` | Operator Setup area |
| REUSABLE | `frontend/src/app/(embed)/concierge/[workspaceId]/[personaId]/page.tsx` | Publish-gated embed |
| EXTENDED (629) | `src/keprix/customer_concierge/capability_health.py` | Honest provider readiness |
| ADDED (630) | `src/keprix/customer_concierge/audience/*` | Durable audience principal, tool policy, embed HMAC, privacy |

### 2. Contract / models

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | `contracts/customer-concierge-v1/` | Vendored schemas + synthetic fixtures |
| ADDED (629) | `src/keprix/customer_concierge/contract_schema.py` | Pydantic validators |
| ADDED (629) | `src/keprix/customer_concierge/scope.py` | `workspace_id`/`tenant_id`/`user_id` mapping |

### 3. viCal bookings / slots / ICS

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | `src/keprix/vical/{bookings,busy,ics,store,routes}.py` | Public booking, guest tokens, ICS |
| INCOMPLETE | `src/keprix/vical/store.py` | JSON file store; not workspace Postgres ledger |
| ADDED (632) | `src/keprix/vical/saga/*` | Provider-neutral booking saga + durable ledger |

### 4. Conferencing

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | `src/keprix/vical/conferencing.py` package (`fallback.py`, `zoom_adapter.py`, `redact.py`) | Templates = unmanaged; Zoom create = managed |
| ADDED (632) | Zoom OAuth + webhooks | `zoom_oauth.py`, `/api/vical/webhooks/zoom`; gap code `zoom_meeting_create` closed |

### 5. Calendar bridge / CalDAV

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | `src/keprix/workspace/routes/calendar_routes.py`, `calendar_sync.py` | Sources + sync presets |
| INCOMPLETE | Soft-fail / unknown invitation projection | Must not leave `confirmed` without usable projection (633) |
| MISSING | Microsoft Graph calendar write | |

### 6. CRM / outreach

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | `src/keprix/crm/*`, `src/keprix/outreach/*` | Durable CRM, Soft Wall, viCal handoff helpers |
| INCOMPLETE | Concierge timeline / outreach stop on booking | Prompt 634 |

### 7. Support / handoff

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | `src/keprix/support/*` | Operator product-support tickets only |
| ADDED (631) | `customer_concierge/{support_cases,handoff,published_knowledge,visitor_turn}.py` | Tenant customer cases + published KB; scope≠product support |

### 8. Gateway / Channel Shield / phone

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | `src/keprix/channel_shield/*` | Web embed adapter, ingest pipeline |
| REUSABLE | Phone receptionist / ECHO persona | Closest product persona; not published concierge |
| ADDED (630) | `customer_concierge/audience/*` | Audience session principal + deny-by-default tools |

### 9. Vault / knowledge / durable stores

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | Credential vault + Document Vault + worker KB | Secrets stay out of prompts |
| REUSABLE | CRM durable SQLite/Postgres pattern | Concierge profiles use SQLite + Alembic 033 |

### 10. Frontend / TUI / desktop

| Status | Path | Note |
| --- | --- | --- |
| REUSABLE | Web `/concierge` + nav contract | Setup first; other tabs shell until 634 |
| INCOMPLETE | Desktop shell deep-link | Uses same web routes when dashboard webview loads `/concierge` |
| INCOMPLETE | TUI concierge commands | Not started |

## Scope mapping (enforced)

| Concept | Keprix field | Rule |
| --- | --- | --- |
| Tenant | `workspace_id` (= `tenant_id`) | Every store query and job filters on this |
| Operator member | `user_id` | Never equal to visitor principal |
| Concierge binding | `persona_id` + `workspace_id` | One profile per binding (628) |

Helper: `src/keprix/customer_concierge/scope.py`.

## Prompt mapping

| Prompt | Extends |
| --- | --- |
| 630 | Audience principal + tool policy (**COMPLETED**) |
| 631 | Published knowledge + external support/handoff (**COMPLETED**) |
| 632 | Booking saga + Zoom create (**COMPLETED**) |
| 633 | Calendar invitations + reconciliation |
| 634 | Operator inbox / CRM / channels UI |
| 635 | E2E packaging and deploy |

## Honesty

Capability health (`GET /api/customer-concierge/capability-health`) reports `ready=false` while Zoom create, calendar projection, and delivery proof remain incomplete. Missing providers report `not_configured`, never fake `ready`.
