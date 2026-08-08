# Carina bridge and dual-run

## Bridge envelope

Passes only:

- worker_id
- persona_version
- approval_id
- keprix_run_id
- tenant
- correlation_ids

Never passes OAuth tokens or bulk private archives.

## Shadow mode

1. Same redacted input to Carina and Keprix.
2. Store quality/safety comparison.
3. **Never publish shadow output.**
4. Dual-write memory is prohibited.
5. Wave 1 memory authority: Keprix draft memory only.

## Circuit breaker

Falls back to Carina behaviour without duplicate draft, approval, notification
or publish action.

## Draft handoff

`POST /v1/products/xeclone/bridge/draft` enters the existing approval path without
changing the live inbound webhook path (still Carina in Phase 1).
