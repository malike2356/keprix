# Governance

## Role x capability matrix

| Capability | viewer | member | admin | owner |
|---|---|---|---|---|
| Read own workspace data | yes | yes | yes | yes |
| Mutate bookings/contacts | no | yes | yes | yes |
| Tenant CRUD | no | no | yes | yes |
| DSAR export/delete request | no | no | yes | yes |
| Governance connect/disconnect | no | no | yes | yes |
| Scout Warden scan request | no | no | yes | yes |
| Billing admin | no | no | yes | yes |

Enforcement: FastAPI `require_admin` for operator mutations; nav/ui_contract filters labels.

## DSAR

Operator UI: `/admin/dsar`

- `POST /api/governance/dsar/export` fulfills via privacy `DsarStore` (JSON export under privacy/exports)
- `POST /api/governance/dsar/delete` requires `confirm=true` (or `dry_run=true`) and calls `erase_user_data`
- `GET /api/governance/dsar/requests`

Also available: `/api/privacy/dsar` and `/api/privacy/erase`.

## Retention

Use privacy retention APIs (`/api/privacy/retention`) and `apply_retention_policies`. Env `KEPRIX_RETENTION_DAYS` is optional operator documentation; policies are the source of truth.
