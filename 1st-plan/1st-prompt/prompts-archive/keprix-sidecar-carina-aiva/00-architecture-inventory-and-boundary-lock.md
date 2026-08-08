# Prompt 516 / CAS-00: Architecture inventory and boundary lock

**Status: COMPLETED 2026-08-08**
**Series:** 516-531 (Carina/Aiva Keprix sidecar)
**Depends on:** product-sidecar contract; soft-separation note
**Blocks:** 517-531
**Writing style:** plain ASCII only.

## Goal

Lock the architecture and inventory before code moves. Prove what already exists
versus what "full Keprix capabilities" still requires.

## Must-haves

1. Document current paths:
   - Keprix `POST /carina/agent/run` + `carina_bridge.py`
   - Carina `KeprixBridgeService` / `CARINA_KEPRIX_URL` / shared token
   - OPS agent-engine switch (`keprix` | `carina`)
   - Existing Carina TypeScript agent loop ownership
2. Gap map: chat turn only vs capability catalog (CRM, Soft Wall, jobs, playbooks,
   viCal, Scout, RAG, channels, data plane).
3. Boundary lock diagram: shell vs brain; southbound allowlist; Soft Wall ownership.
4. Decision: extend foundation pack registry with product keys `carina` and `aiva`
   (not a sixth unrelated product rewrite of Clinicom/Xeclone).
5. Memory authority table by wave (who is SoT for session, CRM, RAG, approvals).
6. Risk register: rewrite trap, dual-write, duplicate side effects, Contabo marketing.
7. Write `docs/architecture/carina-aiva-keprix-sidecar-gap-map.md`.

## Acceptance

- [ ] Gap map lists every Keprix capability family as live / stub / missing / owner-gated
- [ ] Explicit statement that OPS engine flag alone is insufficient
- [ ] Soft separation rule cited; no nested `carina/verlox/` plan

## Done When

517 can define the pack without inventing a second platform tree.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
