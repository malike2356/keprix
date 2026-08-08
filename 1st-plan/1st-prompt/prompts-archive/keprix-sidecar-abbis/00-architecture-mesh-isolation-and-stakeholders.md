# Prompt ABS-00: ABBIS sidecar architecture, mesh, and stakeholder isolation

**Status: COMPLETED 2026-08-08**
**Depends on:** ABBIS spec 26-30, prompts 93-95, 97-98, shared contract
**Blocks:** ABS-01 through ABS-05

## What was built

- domain-packs/abbis/docs/architecture.md
- mesh/mesh.manifest.yaml + isolation six-layer enforcer
- stakeholder/accessory persona bindings


## Goal

Map the complete ABBIS intelligence mesh to a Keprix sidecar without moving SaaS
truth, stakeholder portals, billing, marketplace or Ghana operations into Keprix.

## Must-haves

1. Read ABBIS spec and prompt authorities before writing architecture. Resolve no
   conflict by guessing; ABBIS spec wins and must remain read-only.
2. Inventory all stakeholder personas, modules/accessories, entitlements, tenant
   hierarchy, BDAG scope, field operations, calculators, marketplace, payments,
   compliance, national intelligence, channels, RAG sources and events.
3. Publish responsibility and data-flow maps: ABBIS owns domain truth and access;
   Keprix owns scoped agent sessions, tools, RAG, playbooks and queued AI jobs.
4. Translate each `mesh.manifest` context slice, event, tool and chunker into pack
   registration. Do not create a second intelligence mesh.
5. Enforce six-layer isolation from spec 30 across product, organisation/tenant,
   stakeholder, accessory, project/site and subject. National/BDAG aggregation
   consumes approved de-identified views, never raw cross-tenant records.
6. Define field/offline, low-bandwidth, sidecar-down and channel-degraded flows.
7. Threat model cross-rig leakage, false quotes, unsafe technical advice, payment
   fraud, marketplace manipulation, location exposure, prompt-injected uploads,
   national-data re-identification and unauthorised association access.
8. Preserve operator boundary: ABBIS user-facing identity belongs to its Ghanaian
   operating company; use BDAG exactly; never insert VERLOX as operator.

## Acceptance

- [x] Every stakeholder and accessory has explicit context and grant boundaries
- [x] Mesh registration has one canonical path
- [x] Cross-tenant and national aggregate rules fail closed
- [x] Product works when sidecar and internet are unavailable
