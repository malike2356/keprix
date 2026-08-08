# Prompt PTS-00: Petraclus sidecar architecture, threat model, and boundary

## What was built

- `petraclus/docs/integrations/keprix-sidecar-architecture.md`
- Pack docs: ARCHITECTURE.md, threat-model.md, edition-matrix.md
- Trust zones, target grant object, risk classes, air-gap/degraded behaviour


**Status: COMPLETED 2026-08-08**
**Depends on:** shared product-sidecar contract
**Blocks:** PTS-01 through PTS-05

## Goal

Inventory Petraclus editions and planned runtime, then lock a zero-trust boundary
where Keprix can analyse authorised security data without becoming an unscoped
scanner, credential store, exploit runner, or path around Petraclus licensing.

## Build

1. Publish `docs/integrations/keprix-sidecar-architecture.md` in Petraclus and a
   matching pack contract in Keprix. Inventory Community, Pro and Team surfaces,
   auth, workspaces, assets, scans, findings, evidence, remediation, reports,
   integrations, audit, retention, licence checks and offline operation.
2. Define ownership: Petraclus owns targets, authorisation evidence, finding truth,
   workflows, licences and UI; Keprix owns reasoning, grounded explanation,
   proposed prioritisation, playbooks and policy-gated tools.
3. Threat-model forged target grants, SSRF, prompt injection inside banners/logs,
   malicious scan output, command injection, cross-workspace findings, licence
   bypass, secret leakage, poisoned feeds, report exfiltration and agent escalation.
4. Define trust zones for product API, Keprix pack, sandboxed scanners, feeds,
   report artifacts and optional Scout. No scanner process shares agent privileges.
5. Define target grant object: workspace, target type/value, resolved addresses,
   ports/protocols, allowed techniques, excluded ranges, window, owner evidence,
   approver, expiry and revocation. Revalidate before each active action.
6. Define risk classes: read/explain, passive enrich, safe scan proposal, active
   scan, credentialed scan, exploit validation, remediation. Last three require
   explicit product-side policy and human approval; exploit automation is off.
7. Define Community/Pro/Team capability matrix. Keprix never validates or mints
   licences and always asks Petraclus for current entitlements.
8. Define air-gapped mode, cloud-provider mode, telemetry opt-in, retention and
   encryption expectations without creating phone-home behaviour.

## Acceptance

- [x] Data-flow and threat diagrams cover every trust boundary
- [x] No capability can create its own target authorisation
- [x] Licence authority remains `keys.petraclus.uk` and product-side
- [x] Offline and sidecar-down product behaviour is explicit
