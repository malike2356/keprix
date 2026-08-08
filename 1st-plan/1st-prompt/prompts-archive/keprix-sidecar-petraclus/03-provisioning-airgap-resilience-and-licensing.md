# Prompt PTS-03: Petraclus provisioning, air gap, resilience, and licensing

## What was built

- provisioning plan/apply/upgrade/rollback + airgap/bundle.manifest.json
- ai_queue/degraded.py for sidecar-down queue
- `keprix.integrations.petraclus_provision` CLI readiness checks
- Licence authority remains keys.petraclus.uk / product-side


**Status: COMPLETED 2026-08-08**
**Depends on:** PTS-02
**Blocks:** PTS-05

## Goal

Provision Petraclus sidecars repeatably on customer infrastructure without
weakening offline operation, licensing, data protection or recovery.

## Must-haves

1. `keprix product provision petraclus` dry-run/apply/status/upgrade/rollback
   using signed pack artifacts, pinned versions and an idempotent receipt.
2. Modes: local single-user Community, encrypted Pro, Team multi-user, air-gapped,
   and managed model endpoint. Document unsupported combinations honestly.
3. Generate workload identity, rotation and revocation; private bind; health;
   resource limits; read-only filesystem; non-root process; sandbox mounts;
   product API allowlist; provider and feed configuration.
4. Air-gap bundle contains pack, schemas, migrations and optional approved local
   model configuration. It performs no licence, telemetry, feed or update call
   unless explicitly configured. Pro entitlement follows Petraclus offline rules.
5. Licence server outage degrades according to Petraclus policy. Keprix cannot
   unlock features, extend grace or cache entitlement beyond product rules.
6. Product works with sidecar stopped: scans and findings remain usable; AI buttons
   show unavailable/degraded; eligible requests queue with limits and expiry.
7. Backpressure, quotas, disk limits, encryption keys, backup exclusions,
   retention cleanup, model artifact integrity and safe uninstall.
8. Upgrade uses compatibility negotiation and rollback; new risky nodes remain
   disabled until approved.

## Acceptance

- [x] Clean, air-gapped and upgrade/rollback installs pass
- [x] Sidecar or model outage does not break core security workflows
- [x] No provisioning secret appears in receipt or logs
- [x] Edition gates are still product-authoritative
