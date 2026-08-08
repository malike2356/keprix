# Propreneur Aiva event catalogue

Schema version: `1.0.0`

Propreneur is the source of truth. Outbox rows are written in the same tenant DB transaction as the domain change via `App\Services\Aiva\TransactionalOutbox`.

## Envelope fields

| Field | Required | Notes |
| --- | --- | --- |
| `event_id` | yes | UUID; inbox dedupe key |
| `event` / `event_type` | yes | Catalogue name below |
| `schema_version` | yes | Semver string; reject unsupported |
| `tenant_id` | yes | Propreneur tenant key |
| `resource_type` | yes | e.g. `property`, `contact` |
| `resource_id` | yes | String id |
| `resource_version` | yes | Monotonic aggregate version |
| `occurred_at` | yes | ISO-8601 |
| `correlation_id` | no | Request / proposal correlation |
| `changed_fields` | no | Minimal keys only; no secrets |

Delivery also includes `workerId`, `tenantSlug`, and HMAC header `X-Propreneur-Signature`.

## Event names

| Event | When |
| --- | --- |
| `property.created` | Property inserted |
| `property.updated` | Property fields changed |
| `property.archived` | Soft-archived |
| `property.restored` | Restored from archive |
| `property.status_changed` | Status transition |
| `contact.created` | Contact inserted |
| `contact.updated` | Contact changed |
| `contact.archived` | Contact archived |
| `tenancy.created` | Tenancy started |
| `tenancy.updated` | Tenancy changed |
| `tenancy.status_changed` | Tenancy status |
| `tenancy.assignment_changed` | Assignee / manager changed |
| `deal.created` | Deal created |
| `deal.updated` | Deal updated |
| `deal.status_changed` | Pipeline stage / status |
| `maintenance.created` | Maintenance request created |
| `maintenance.updated` | Maintenance updated |
| `maintenance.status_changed` | Status transition |
| `compliance.updated` | Certificate / compliance item changed |
| `approval.changed` | Bridge proposal approved / rejected |
| `access.revoked` | Membership, grant, or link revoked |
| `email_processed` | Inbound email classified (legacy notification) |

## Versioning policy

- Bump `schema_version` minor for additive fields; major for renames or removals.
- Consumers must reject unsupported major versions and surface schema incompatibility in sync health.
- Old and new consumers must coexist during rolling releases by ignoring unknown optional fields.

## Sensitive fields

Omit passwords, tokens, API keys, webhook secrets, and full payment card data from payloads. Aiva retrieves sensitive detail on demand through the governed API when authorized.
