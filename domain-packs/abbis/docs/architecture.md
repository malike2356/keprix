# ABS-00: ABBIS sidecar architecture

## Responsibility map

| Owner | Owns |
| --- | --- |
| ABBIS (Ghanaian operating company) | Users, tenancy, entitlements, records, billing, portals, marketplace, Ghana operations, localisation copy |
| BDAG | Association AMS, approved national aggregates (de-identified) |
| Keprix sidecar | Scoped sessions, capability nodes, deterministic calculators, RAG retrieval, playbooks, AI queues, audit of AI actions |

Keprix never receives unrestricted DB access and never becomes a hidden product backend.

## Data flow

1. Product issues short-lived token (tenant, stakeholder, grants, purpose).
2. Sidecar creates session and advertises entitled nodes only.
3. `/invoke` validates pack node, grants, accessory, tenant, purpose and schema.
4. Deterministic formulas run in-pack; LLM may explain only.
5. Writes return proposals; product preview/apply commits with idempotency + approval.
6. Events ingest at-least-once with dedupe; product remains usable when sidecar is down.

## Six-layer isolation

1. Product (`abbis` only)
2. Organisation / tenant
3. Stakeholder persona (JWT, never from user text)
4. Accessory entitlement
5. Project / site
6. Subject (worker/client record)

National/BDAG aggregation consumes approved de-identified views with min cell threshold (>=5). Never raw cross-tenant records.

## Degraded modes (spec 28)

- `FULL`, `AI_DEGRADED`, `CHANNEL_DEGRADED`, `CORE_MAINTENANCE`, `OUTAGE`
- Product core + native calculators continue when Keprix is down
- Eligible AI work queues with TTL, priority, dedupe; replay revalidates authority

## Threat model (summary)

| Threat | Control |
| --- | --- |
| Cross-rig / cross-tenant leakage | IsolationEnforcer on every invoke and product endpoint |
| False quotes | Deterministic quote calculator + no Kari/KB prefixes |
| Unsafe technical advice | High-risk nodes propose only; human review |
| Payment / marketplace fraud | Soft-wall approvals + product apply |
| Location exposure in channels | Minimise fields; block sensitive group chat writes |
| Prompt-injected uploads | Treat uploads as untrusted RAG data |
| National re-identification | Aggregate schemas + cell threshold |
| Unauthorised association access | S14/S01/platform only for national nodes |

## Operator boundary

User-facing identity belongs to the Ghanaian operating company. Association name is **BDAG** only. Never insert VERLOX as operator.
