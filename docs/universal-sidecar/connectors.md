# Connectors

Southbound calls from Keprix to the product use **declared** connector
operations only. Default deny applies to any undeclared route.

## Declaring an operation

```yaml
connectors:
  - key: order.get
    method: GET
    path: /api/orders/{id}
    purpose: Fetch one order
    mode: read          # read | preview | propose | apply
    sensitivity: pii_minimised
    grants: [connector:order.get]
    timeout_seconds: 15
    rate_per_minute: 60
    projection: [id, status, total]
    approval_required: false
    idempotency: false
```

## Modes

| Mode | Meaning |
| --- | --- |
| `read` | Safe fetch / list |
| `preview` | Dry-run of a mutation |
| `propose` | Prepare a change without applying |
| `apply` | Perform a side effect (usually approval-gated) |

## Product minimum endpoints (recommended)

- `GET /api/keprix/v1/health`
- `GET /api/keprix/v1/capabilities`
- `POST /api/keprix/v1/token/exchange`
- `GET /api/keprix/v1/context`
- `POST /api/keprix/v1/events/ack`

Plus product-specific read and action endpoints with pagination, projection,
idempotency keys, and approval evidence.

## Rules

- No scraping of internal UI routes
- No undocumented private endpoints
- No direct SQL credentials
- Egress allowlists and SSRF controls apply to every URL
- Test connectors with `POST .../connectors/{key}/test` (discover scope)
