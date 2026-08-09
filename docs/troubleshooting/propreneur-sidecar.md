# Propreneur sidecar troubleshooting

Keprix exposes a **propreneur** product pack under the shared product sidecar (`/v1/products/propreneur/...`). Propreneur Laravel calls Keprix (often Contabo loopback `http://127.0.0.1:13333`) and Keprix calls back into Propreneur tool HTTP with a shared token.

## Symptom: Propreneur chat cannot use tools

**Fix:** Confirm engine is `keprix`, shared token matches both sides, and Propreneur tool callbacks send an explicit `user_id` / actor (fail-closed; no first-user fallback).

## Symptom: Mutations duplicate or hang after approval

**Fix:** Check Keprix tool execution ledger / idempotency keys and Soft Wall-style approvals on the Propreneur side. Do not retry an ambiguous mutation through a second engine.

## Symptom: Circuit open / Keprix unavailable

**Fix:** Health-check Keprix; wait for circuit cooldown; use emergency disable / native engine only when policy allows pre-mutation fallback.

## Related docs

- [Propreneur sidecar README](../propreneur-sidecar/README.md)
- [Key rotation](../propreneur-sidecar/key-rotation.md)
- [Observability runbook](../propreneur-sidecar/observability-runbook.md)
- [Canary cutover](../propreneur-sidecar/canary-cutover-rollback.md)
- [Release manifest](../operations/propreneur-sidecar-release-manifest.md)
- [Universal sidecar troubleshooting](../universal-sidecar/troubleshooting.md)
