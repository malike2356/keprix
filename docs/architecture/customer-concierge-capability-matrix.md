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
| Public viCal booking / ICS | PARTIAL | `vical/*`; no saga confirmation rules |
| Conferencing (Zoom create) | MISSING | `conferencing.py` template only |
| Google calendar projection | PARTIAL | Workspace calendar bridge; no concierge saga |
| Microsoft calendar | MISSING | Not live |
| Outbound delivery proof | MISSING | `vical/notifications.py` in-memory outbox |
| External customer support | MISSING | `support/routes.py` operator-auth |
| Audience session principal | REAL | Prompt 630; `customer_concierge/audience/*` deny-by-default tools |
| Channel Shield web path | PARTIAL | Embed HMAC + origin allowlist; gateway adapter still broader |
| Carina runtime dependency | OUT_OF_SCOPE | Forbidden; static import scan |

Conformance: `tests/customer_concierge/test_contract_conformance_629.py`.
