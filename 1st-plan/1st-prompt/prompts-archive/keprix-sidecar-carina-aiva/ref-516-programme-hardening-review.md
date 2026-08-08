# Hardening review: Carina/Aiva Keprix sidecar programme

**Status: COMPLETED 2026-08-08** (was BINDING)
**Date:** 2026-08-08
**Writing style:** plain ASCII only.

## Verdict frame

Switch the **brain** (agent runtime + capability execution) to Keprix.
Keep the **body** (Carina/Aiva UI, auth, billing, Soft Wall operator UI, records).

## Must controls

1. **No unrestricted tool executor.** `/invoke` only runs advertised pack nodes.
2. **No product DB credentials in Keprix.** Southbound allowlisted API only.
3. **No dual-write memory.** Explicit authority per wave.
4. **Soft Wall stays one system.** Product UI decides; Keprix requests approval
   evidence; do not invent a second approval bus.
5. **Tenant isolation.** Workspace A cannot read workspace B context, memory,
   jobs, CRM, or approvals.
6. **Carina vs Aiva soft separation.** Shared runtime changes go to Carina core;
   Aiva-only packaging stays in Aiva paths. One pack family, thin product wrappers.
7. **Shadow cannot publish.** Dual-run outputs are comparison-only until cutover.
8. **Fallback cannot duplicate side effects.** Idempotency keys on every mutate/
   outbound node.
9. **OPS honesty.** `global_engine=keprix` means live invoke path, not health ping
   alone.
10. **Contabo marketing.** Never leave `carinaai.uk` broken after deploy.
11. **Stripe.** Never create prices; read `.access` SoT only.
12. **Scout / Clinicom OPS.** Do not fold into Carina OPS.

## Capability exposure priority (Must for "full capabilities")

P0 (chat cutover): agent run, tool routing, prompt guard, kill switch, budgets.
P1: Soft Wall approvals, CRM read/propose, enroll Soft Wall, bookings (viCal).
P2: discovery jobs, outreach outbox, Scout hooks, RAG admin, playbooks/jobs.
P3 Nice: licensed enrich live keys, WA/SMS live keys, social OAuth, portal feeds
(remain owner-gated even if nodes exist as `not_configured`).

## Explicit refusals

- Rebuild hireaiva frontend inside Keprix.
- Copy OAuth provider tokens into Keprix prompts or logs.
- Cross-product memory retrieval Carina <-> Clinicom <-> Petraclus.
- HTML scrape adapters as default "full capability".

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
