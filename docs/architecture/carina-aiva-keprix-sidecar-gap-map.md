# Carina/Aiva Keprix sidecar gap map

**Status:** LOCKED (CAS-00)
**Date:** 2026-08-08
**Writing style:** plain ASCII only.

## Verdict

Carina/Aiva already had a **chat-turn bridge** (`POST /carina/agent/run`).
That is not "full Keprix capabilities". OPS `global_engine=keprix` alone is
**insufficient** until primary invoke path and capability catalog succeed.

## Boundary lock

```
[Carina/Aiva shell]
  auth, orgs, billing, Soft Wall UI, records, hireaiva UX
        |  northbound /v1/products/{carina|aiva}
        v
[Keprix brain]
  advertised capability nodes only (no free tool executor)
        |  southbound allowlisted /api/keprix/v1/*
        v
[Carina/Aiva product API]
  projected reads, approval evidence, idempotent applies
```

Soft Wall: **one bus**, product-owned UI. Keprix requests approval evidence.
No nested `carina/verlox/` tree. Soft separation:
`shared/workspace-governance/CARINA-AIVA-SOFT-SEPARATION.md`.

## Existing pieces

| Piece | Path | Role |
| --- | --- | --- |
| Legacy bridge | `keprix/.../carina_bridge.py`, `POST /carina/agent/run` | Compat chat turn |
| PHP client | `carina/app/Services/Carina/KeprixBridgeService.php` | Shared-token caller |
| OPS switch | `core.carinaai.uk` agent-engine | Engine assignment |
| CRM Soft Wall | `keprix/crm/soft_wall.py` | Native CRM gates |

## Capability family status

| Family | Status | Notes |
| --- | --- | --- |
| agent.run / interrupt | live | Compat + `/invoke` |
| soft_wall.* | live | Product deep links |
| crm.* read/propose/enroll/pipeline/analytics | live | Soft Wall on mutate/outbound |
| discovery / outreach | live | Soft Wall + idempotency |
| vical / booking | live | Soft Wall on offer |
| scout.hooks | live | Hooks only; Scout remains console |
| memory / rag | live | Wave authority below |
| playbook / jobs / channels.notify / data.* | live | Export Soft Wall |
| licensed enrich / WA / SMS / social OAuth | not_configured | Owner-gated Nice |
| Cross Clinicom/Petraclus composition | denied | Fail closed |

## Memory authority table

| Wave | Session memory SoT | CRM records | Soft Wall | RAG indexes |
| --- | --- | --- | --- | --- |
| Shadow | Carina (Keprix ephemeral traces only) | Product/Keprix CRM via capabilities | Product UI | Workspace scoped; no dual-write |
| Keprix primary | Keprix session for agent turns | Same | Product UI | Same |
| Always | No silent dual-write of same document | Product SoT via southbound for apply | One bus | DSAR propagates |

## Risk register

1. Rewrite trap: rebuilding hireaiva inside Keprix. Mitigate: shell stays Carina/Aiva.
2. Dual-write memory. Mitigate: authority table + shadow ephemeral.
3. Duplicate side effects on fallback. Mitigate: idempotency keys + circuit.
4. Contabo marketing 403. Mitigate: never-break rule; prefer product-scoped deploys.
5. OPS lying via health ping. Mitigate: primary invoke probe.

## Decision

Extend product-sidecar foundation with product keys `carina` and `aiva`
(Aiva wrapper of shared Carina nodes). Not a sixth unrelated product rewrite.
