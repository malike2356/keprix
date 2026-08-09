# Customer Concierge capability matrix (Prompt 629)

**Status:** BASELINE LOCKED  
**Date:** 2026-08-09  
**Series:** `keprix-customer-concierge-booking` (628-635)  
**Contract:** `contracts/customer-concierge-v1/` (version 1.0.0)

Classification: **REAL** | **PARTIAL** | **SIMULATED** | **MISSING** | **OUT_OF_SCOPE**

Honesty rule: URL templates, in-memory outboxes, and operator-auth support routes never mark REAL for managed Zoom booking or external customer support.

| Capability | Status | Evidence |
| --- | --- | --- |
| Concierge setup wizard + publish | REAL | Prompt 628; `customer_concierge` package |
| Contract schemas + synthetic fixtures | REAL | Vendored contract; `contract_schema.py` |
| Scope mapping workspace/tenant/user | REAL | `scope.py` + store queries by workspace |
| Capability health (CE + Postgres label) | REAL | `capability_health.py`; CE defaults `not_configured` |
| Public viCal booking / ICS | REAL | Saga + ICS CE path; ATTENDEE in ICS |
| Conferencing (Zoom create) | REAL | Prompt 632; `vical/conferencing/zoom_adapter.py` + `book_with_saga` |
| Google calendar projection | REAL | Prompt 633; `vical/calendar/google_adapter.py` + saga project |
| Microsoft calendar | PARTIAL | Adapter present; live OAuth store still a gap |
| Outbound delivery proof | PARTIAL | Durable SQLite outbox evidence; SMTP ACK optional |
| External customer support | REAL | Prompt 631; `customer_concierge/support_cases.py` (not `/api/support`) |
| Published business knowledge | REAL | Prompt 631; `published_knowledge.py` publish_state + citations |
| Audience session principal | REAL | Prompt 630; `customer_concierge/audience/*` deny-by-default tools |
| Channel Shield web path | PARTIAL | Embed HMAC + origin allowlist; gateway adapter still broader |
| Operator Bookings/Channels/Analytics UI | REAL | Prompt 634; concierge page tabs + workspace_surface APIs |
| CRM/Outreach booking mesh | REAL | Prompt 634; capability_mesh + nurture_orchestration |
| Outreach stop on booking / pause on case | REAL | Soft Wall status booked + paused_support |
| E2E / packaging (635) | REAL | Hermetic journey, signed fixtures, runbook, Contabo evidence |
| Carina runtime dependency | OUT_OF_SCOPE | Forbidden; static import scan |

Conformance: `tests/customer_concierge/test_contract_conformance_629.py`.
