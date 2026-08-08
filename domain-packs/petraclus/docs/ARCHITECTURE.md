# Petraclus sidecar architecture (pack-local)

## Ownership

| Concern | Owner |
| --- | --- |
| Targets, authorisation evidence, finding truth, workflows, licences, UI | Petraclus |
| Reasoning, grounded explanation, proposed prioritisation, playbooks, gated tools | Keprix |

Licence authority remains product-side / `keys.petraclus.uk`.

## Trust zones

1. **Product API** (Petraclus): authoritative reads/writes, grants, entitlements.
2. **Keprix pack** (this sidecar): policy-gated nodes; fail closed isolation.
3. **Sandboxed scanners**: no shared privileges with the agent process.
4. **Feeds**: untrusted inbound intel; injection detection; no tool trigger from text.
5. **Report artifacts**: provenance-labelled; publish is product action.
6. **Optional Scout**: monitoring only; cannot mint grants or licences.

## Data flow

```
Operator UI (Petraclus)
  -> Product API (grants, findings, approvals, entitlements)
  -> Keprix sidecar /v1/products/petraclus/*
       -> IsolationEnforcer (product, workspace, edition, role, target grant, purpose)
       -> Connector allowlist (default deny)
       -> Handlers (read / analyse / propose / gated action)
```

## Risk classes

- read / passive_enrich: explain and search within workspace
- propose: soft wall + preview hash
- active_scan / credentialed_scan / mutate / outbound: exact grant + approval + edition; revalidate each time
- exploit validation / remediation execute: not shipped

## Modes

FULL, AIRGAP, DEGRADED via `PETRACLUS_PLATFORM_MODE`. Air-gap bundle has no phone-home unless configured.
