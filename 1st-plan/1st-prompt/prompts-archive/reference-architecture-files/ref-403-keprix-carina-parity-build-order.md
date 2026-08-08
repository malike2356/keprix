# Ref 403: Keprix close Carina parity gaps (build order)

Status: COMPLETED 2026-08-04 (archived 2026-08-07)  
Source: `/opt/lampp/htdocs/verlox/archive/keprix-carina-parity-gap-2026-07-30.md`  
Series archive: `403-415-*.md` (was `../pending-prompts/keprix-carina-parity/`)  
Sister: Carina inbound archived obsolete-by-sidecar under `carina/.../carina-keprix-parity-obsolete-by-sidecar`

## Order

| ID | Intent |
|---|---|
| 403 | Stale gap refresh |
| 404 | Multi-tenancy foundation (CRITICAL) |
| 405 | Tenant isolation enforcement (CRITICAL) |
| 406 | Governance / GDPR / RBAC |
| 407 | AI security beyond 372-375 |
| 408 | Scout Warden integration |
| 409 | Domain pack library |
| 410 | Product tools layer |
| 411 | RAG admin |
| 412 | Self-knowledge depth |
| 413 | Billing promo/trial/BYOK |
| 414 | Conditional workflows |
| 415 | CI/CD security workflows |

## Parallelism

- 409 can start after 00.
- 411/412 after 00; prefer after mesh.
- 404 then 405 strictly sequential.
- 413 needs 405.
- 408 after 407 preferred.
