# Fleetz sidecar pilot sign-off

**Date:** 2026-08-08  
**Mode:** Read-only / advisory Ghana pilot readiness  
**Vehicle commands:** NOT READY (remain disabled)

## Pilot constraints

- Small owned fleet with known sensor calibration
- Human-reviewed cases only
- Immediate kill switch via `POST /v1/products/fleetz/ops/kill-switch`
- Support owner: Fleetz ops + Keprix pack maintainer
- Thresholds: refuse stale series; no theft accusations; idempotent outbound

## Evidence checklist

| Check | Status |
| --- | --- |
| Health and capability negotiation | Covered by tests + local deploy |
| Cross-fleet isolation | `test_cross_fleet_isolation` |
| Command attempts fail closed | `test_command_nodes_denied` |
| Stale/insufficient refusal | `test_stale_and_insufficient_refusal` |
| Deterministic calculators | `test_deterministic_fuel_and_maintenance` |
| Duplicate notification prevention | `test_idempotent_notification_and_playbooks` |
| Event storm coalesce within budget | `test_event_storm_coalesce_and_provision` |
| Prompt injection / precise export denied | `test_security_prompt_injection_and_precise_export` |
| Provision receipt without secrets | `provision/provisioner.py` |
| Rollback drains without replaying notifications | `rollback()` receipt fields |
| Primary tracking independence | Sidecar stop does not touch Fleetz ingest (architecture) |

## Explicit non-goals for this pilot

- Immobilise / fuel cut / tracker config / firmware
- Live geofence apply
- Contabo production deploy of Fleetz product (product app not yet built)

## Sign-off

Pack version `0.1.0` is ready for capped staging advisory use against fixtures or a
future Fleetz `/api/keprix/v1` surface. Vehicle command capabilities remain NOT READY
until an independent safety programme is explicitly approved.
