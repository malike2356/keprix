# Prompt 503 / 36: Credential proxy and vault ops GUI polish (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/api/admin/proxy` status/doctor/cordon Soft Wall; credentials ProxyOpsPanel


**Depends on:** 467, existing vault/credentials dashboard pages
**Blocks:** 505

## Goal

Dashboard credentials exist; keprix-proxy doctor/cordon and production proxy ops
remain CLI/API-heavy. Give admins a safe GUI for status and Soft Wall cordon.

## Must-haves

1. Extend `/dashboard/credentials` and/or `/admin` with proxy status panel:
   health, cordon state, last doctor report summary.
2. Soft Wall for cordon on/off and forced rotation triggers.
3. Link vault setup; never display raw secrets.
4. Reuse proxy APIs/CLI backends; do not fork secret stores.
5. Nav label honesty; docs; tests.
6. Edition/self-host notes for OSS vs managed.

## Acceptance

- [x] Admin views proxy health from GUI
- [x] Cordon Soft Wall gated
- [x] No secret values in UI/network responses beyond last4/metadata

## Done When

Proxy incident response has a GUI path.
